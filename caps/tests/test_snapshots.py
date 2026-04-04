# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS — Capability Snapshot Tests
=================================

Tests for api_snapshots.py:
 - take_snapshot
 - compare_snapshots
 - compare_with_current
 - get_snapshot_history
 - restore_snapshot (dry run + apply)

Prefix: capstest_snap_

Run with:
    bench --site dev.localhost run-tests --app caps \
        --module caps.tests.test_snapshots
"""

import json
import frappe
import unittest

_TEST_PREFIX = "capstest_snap_"

_CAPS = {
    "alpha": f"{_TEST_PREFIX}cap:alpha",
    "beta": f"{_TEST_PREFIX}cap:beta",
    "gamma": f"{_TEST_PREFIX}cap:gamma",
}

_USERS = {
    "main": f"{_TEST_PREFIX}main@test.local",
}


def _setup_snapshot_data():
    _teardown_snapshot_data()

    # Create capabilities
    for key, name in _CAPS.items():
        frappe.get_doc({
            "doctype": "Capability",
            "name1": name,
            "label": f"Snap {key}",
            "category": "Custom",
            "is_active": 1,
        }).insert(ignore_permissions=True)

    # Create test user
    user = frappe.get_doc({
        "doctype": "User",
        "email": _USERS["main"],
        "first_name": "SnapMain",
        "send_welcome_email": 0,
        "roles": [{"role": "System Manager"}],
    })
    user.insert(ignore_permissions=True)

    # Assign alpha + beta directly
    uc = frappe.get_doc({
        "doctype": "User Capability",
        "user": _USERS["main"],
        "direct_capabilities": [
            {"capability": _CAPS["alpha"]},
            {"capability": _CAPS["beta"]},
        ],
    })
    uc.insert(ignore_permissions=True)

    frappe.db.commit()
    _flush(_USERS["main"])


def _teardown_snapshot_data():
    # Clean snapshots
    for name in frappe.get_all(
        "Capability Snapshot",
        filters={"user": ("like", f"{_TEST_PREFIX}%")},
        pluck="name",
    ):
        frappe.delete_doc("Capability Snapshot", name, force=True, ignore_permissions=True)

    # Clean user capabilities
    for name in frappe.get_all(
        "User Capability",
        filters={"user": ("like", f"{_TEST_PREFIX}%")},
        pluck="name",
    ):
        frappe.delete_doc("User Capability", name, force=True, ignore_permissions=True)

    # Clean capabilities
    for cap_name in _CAPS.values():
        if frappe.db.exists("Capability", cap_name):
            frappe.delete_doc("Capability", cap_name, force=True, ignore_permissions=True)

    # Clean imported caps from restore tests
    for name in frappe.get_all(
        "Capability",
        filters={"name1": ("like", f"{_TEST_PREFIX}%")},
        pluck="name",
    ):
        frappe.delete_doc("Capability", name, force=True, ignore_permissions=True)

    # Clean audit logs
    frappe.db.sql(
        "DELETE FROM `tabCAPS Audit Log` WHERE capability LIKE %s",
        (f"{_TEST_PREFIX}%",),
    )

    for email in _USERS.values():
        _safe_delete_user(email)

    frappe.db.commit()


def _safe_delete_user(email):
    """Delete user, handling linked docs from other apps (e.g. Gameplan)."""
    if not frappe.db.exists("User", email):
        return
    try:
        frappe.delete_doc("User", email, force=True, ignore_permissions=True)
    except Exception:
        try:
            for dt in ("GP User Profile",):
                for name in frappe.get_all(dt, filters={"user": email}, pluck="name"):
                    frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        except Exception:
            pass


def _flush(user):
    frappe.cache.delete_value(f"caps:user:{user}")


class TestSnapshots(unittest.TestCase):
    """Test Capability Snapshot functionality."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        _setup_snapshot_data()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        _teardown_snapshot_data()

    def setUp(self):
        frappe.set_user("Administrator")

    # ─── take_snapshot ─────────────────────────────────────────────

    def test_take_snapshot_creates_doc(self):
        """take_snapshot should create a Capability Snapshot document."""
        from caps.api_snapshots import take_snapshot
        result = take_snapshot(user=_USERS["main"], label="Test Snap 1")
        self.assertIsNotNone(result)
        self.assertEqual(result["user"], _USERS["main"])
        self.assertEqual(result["snapshot_label"], "Test Snap 1")
        self.assertTrue(frappe.db.exists("Capability Snapshot", result["name"]))

    def test_take_snapshot_captures_capabilities(self):
        """Snapshot JSON should contain the user's resolved capabilities."""
        from caps.api_snapshots import take_snapshot
        result = take_snapshot(user=_USERS["main"], label="Cap check")
        data = json.loads(result["capabilities_json"])
        caps = data.get("resolved_capabilities", [])
        self.assertIn(_CAPS["alpha"], caps)
        self.assertIn(_CAPS["beta"], caps)

    def test_take_snapshot_includes_sources(self):
        """Snapshot JSON should include capability source breakdown."""
        from caps.api_snapshots import take_snapshot
        result = take_snapshot(user=_USERS["main"], label="Sources check")
        data = json.loads(result["capabilities_json"])
        sources = data.get("sources", {})
        self.assertIn("direct", sources)
        self.assertIn(_CAPS["alpha"], sources["direct"])

    def test_take_snapshot_invalid_user_throws(self):
        """take_snapshot with non-existent user should throw."""
        from caps.api_snapshots import take_snapshot
        with self.assertRaises(Exception):
            take_snapshot(user="nonexistent@nobody.local")

    def test_take_snapshot_source_field(self):
        """Snapshot should record the source (manual/scheduled/etc)."""
        from caps.api_snapshots import take_snapshot
        result = take_snapshot(
            user=_USERS["main"], label="Src Test", source="pre_change"
        )
        self.assertEqual(result["source"], "pre_change")

    # ─── compare_snapshots ─────────────────────────────────────────

    def test_compare_snapshots_finds_diff(self):
        """Comparing two snapshots should show added/removed/unchanged."""
        from caps.api_snapshots import take_snapshot, compare_snapshots

        # Snapshot 1: alpha + beta
        snap1 = take_snapshot(user=_USERS["main"], label="Before")

        # Add gamma
        uc = frappe.get_doc("User Capability", _USERS["main"])
        uc.append("direct_capabilities", {"capability": _CAPS["gamma"]})
        uc.save(ignore_permissions=True)
        frappe.db.commit()
        _flush(_USERS["main"])

        # Snapshot 2: alpha + beta + gamma
        snap2 = take_snapshot(user=_USERS["main"], label="After")

        diff = compare_snapshots(snap1["name"], snap2["name"])
        self.assertIn(_CAPS["gamma"], diff["added"])
        self.assertEqual(diff["removed"], [])
        self.assertIn(_CAPS["alpha"], diff["unchanged"])
        self.assertEqual(diff["added_count"], 1)

        # Cleanup: remove gamma
        uc = frappe.get_doc("User Capability", _USERS["main"])
        uc.direct_capabilities = [
            row for row in uc.direct_capabilities
            if row.capability != _CAPS["gamma"]
        ]
        uc.save(ignore_permissions=True)
        frappe.db.commit()
        _flush(_USERS["main"])

    def test_compare_snapshots_shows_removal(self):
        """Comparing snapshots should detect removals."""
        from caps.api_snapshots import take_snapshot, compare_snapshots

        # Snapshot 1: alpha + beta
        snap1 = take_snapshot(user=_USERS["main"], label="Before removal")

        # Remove beta
        uc = frappe.get_doc("User Capability", _USERS["main"])
        uc.direct_capabilities = [
            row for row in uc.direct_capabilities
            if row.capability != _CAPS["beta"]
        ]
        uc.save(ignore_permissions=True)
        frappe.db.commit()
        _flush(_USERS["main"])

        # Snapshot 2: alpha only
        snap2 = take_snapshot(user=_USERS["main"], label="After removal")

        diff = compare_snapshots(snap1["name"], snap2["name"])
        self.assertIn(_CAPS["beta"], diff["removed"])
        self.assertEqual(diff["removed_count"], 1)

        # Restore beta
        uc = frappe.get_doc("User Capability", _USERS["main"])
        uc.append("direct_capabilities", {"capability": _CAPS["beta"]})
        uc.save(ignore_permissions=True)
        frappe.db.commit()
        _flush(_USERS["main"])

    # ─── compare_with_current ──────────────────────────────────────

    def test_compare_with_current(self):
        """compare_with_current should diff snapshot vs live state."""
        from caps.api_snapshots import take_snapshot, compare_with_current

        snap = take_snapshot(user=_USERS["main"], label="Baseline")

        # Add gamma to current
        uc = frappe.get_doc("User Capability", _USERS["main"])
        uc.append("direct_capabilities", {"capability": _CAPS["gamma"]})
        uc.save(ignore_permissions=True)
        frappe.db.commit()
        _flush(_USERS["main"])

        diff = compare_with_current(snap["name"])
        self.assertIn(_CAPS["gamma"], diff["added"])
        self.assertEqual(len(diff["removed"]), 0)
        self.assertGreater(diff["current_count"], diff["snapshot_info"]["count"])

        # Cleanup
        uc = frappe.get_doc("User Capability", _USERS["main"])
        uc.direct_capabilities = [
            row for row in uc.direct_capabilities
            if row.capability != _CAPS["gamma"]
        ]
        uc.save(ignore_permissions=True)
        frappe.db.commit()
        _flush(_USERS["main"])

    # ─── get_snapshot_history ──────────────────────────────────────

    def test_get_snapshot_history(self):
        """get_snapshot_history should return list of user's snapshots."""
        from caps.api_snapshots import take_snapshot, get_snapshot_history

        # Take at least one snapshot
        take_snapshot(user=_USERS["main"], label="History test")

        history = get_snapshot_history(user=_USERS["main"])
        self.assertIsInstance(history, list)
        self.assertGreaterEqual(len(history), 1)
        self.assertEqual(history[0]["user"], _USERS["main"])
        self.assertIn("capability_count", history[0])

    def test_get_snapshot_history_filter_by_source(self):
        """get_snapshot_history should filter by source when specified."""
        from caps.api_snapshots import take_snapshot, get_snapshot_history

        take_snapshot(user=_USERS["main"], label="Sched", source="scheduled")

        history = get_snapshot_history(user=_USERS["main"], source="scheduled")
        for s in history:
            self.assertEqual(s["source"], "scheduled")

    def test_get_snapshot_history_limit(self):
        """get_snapshot_history should respect limit parameter."""
        from caps.api_snapshots import take_snapshot, get_snapshot_history

        # Take a few snapshots
        for i in range(3):
            take_snapshot(user=_USERS["main"], label=f"Limit test {i}")

        history = get_snapshot_history(user=_USERS["main"], limit=2)
        self.assertLessEqual(len(history), 2)

    # ─── restore_snapshot ──────────────────────────────────────────

    def test_restore_snapshot_dry_run(self):
        """restore_snapshot dry_run should show changes without applying."""
        from caps.api_snapshots import take_snapshot, restore_snapshot

        snap = take_snapshot(user=_USERS["main"], label="For restore dry")

        # Add gamma
        uc = frappe.get_doc("User Capability", _USERS["main"])
        uc.append("direct_capabilities", {"capability": _CAPS["gamma"]})
        uc.save(ignore_permissions=True)
        frappe.db.commit()
        _flush(_USERS["main"])

        result = restore_snapshot(snap["name"], dry_run=True)
        self.assertFalse(result["applied"])
        # gamma was added after snapshot, so restoring would revoke it
        self.assertIn(_CAPS["gamma"], result["to_revoke"])

        # Cleanup
        uc = frappe.get_doc("User Capability", _USERS["main"])
        uc.direct_capabilities = [
            row for row in uc.direct_capabilities
            if row.capability != _CAPS["gamma"]
        ]
        uc.save(ignore_permissions=True)
        frappe.db.commit()
        _flush(_USERS["main"])

    def test_restore_snapshot_apply(self):
        """restore_snapshot with dry_run=False should actually apply changes."""
        from caps.api_snapshots import take_snapshot, restore_snapshot
        from caps.utils.resolver import resolve_capabilities

        # Take baseline snapshot (alpha + beta)
        snap = take_snapshot(user=_USERS["main"], label="For restore apply")

        # Add gamma
        uc = frappe.get_doc("User Capability", _USERS["main"])
        uc.append("direct_capabilities", {"capability": _CAPS["gamma"]})
        uc.save(ignore_permissions=True)
        frappe.db.commit()
        _flush(_USERS["main"])

        # Verify gamma is now present
        current = resolve_capabilities(_USERS["main"])
        self.assertIn(_CAPS["gamma"], current)

        # Restore to snapshot (should remove gamma)
        result = restore_snapshot(snap["name"], dry_run=False)
        self.assertTrue(result["applied"])
        self.assertIn(_CAPS["gamma"], result["to_revoke"])

        # Verify gamma is gone
        _flush(_USERS["main"])
        after = resolve_capabilities(_USERS["main"])
        self.assertNotIn(_CAPS["gamma"], after)
        # alpha + beta should still be there
        self.assertIn(_CAPS["alpha"], after)
        self.assertIn(_CAPS["beta"], after)

    def test_restore_creates_post_change_snapshot(self):
        """restore_snapshot should create a post_change snapshot."""
        from caps.api_snapshots import take_snapshot, restore_snapshot

        snap = take_snapshot(user=_USERS["main"], label="Pre-restore")

        # Apply restore (even if no changes, it should still create post-snapshot)
        restore_snapshot(snap["name"], dry_run=False)

        # Check that a post_change snapshot was created
        post_snaps = frappe.get_all(
            "Capability Snapshot",
            filters={
                "user": _USERS["main"],
                "source": "post_change",
            },
            pluck="name",
        )
        self.assertGreaterEqual(len(post_snaps), 1)
