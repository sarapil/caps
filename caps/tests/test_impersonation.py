"""
CAPS — Impersonation Tests
============================

Tests for api_impersonation.py:
 - start_impersonation
 - stop_impersonation
 - get_impersonation_status
 - resolver integration (impersonated user sees target's caps)
 - audit trail

Prefix: capstest_imp_

Run with:
    bench --site dev.localhost run-tests --app caps \
        --module caps.tests.test_impersonation
"""

import frappe
import unittest

_TEST_PREFIX = "capstest_imp_"

_CAPS = {
    "admin_only": f"{_TEST_PREFIX}cap:admin_only",
    "target_only": f"{_TEST_PREFIX}cap:target_only",
    "shared": f"{_TEST_PREFIX}cap:shared",
}

_USERS = {
    "admin": f"{_TEST_PREFIX}admin@test.local",
    "target": f"{_TEST_PREFIX}target@test.local",
}


def _setup_impersonation_data():
    _teardown_impersonation_data()

    # Create capabilities
    for key, name in _CAPS.items():
        frappe.get_doc({
            "doctype": "Capability",
            "name1": name,
            "label": f"Imp {key}",
            "category": "Custom",
            "is_active": 1,
        }).insert(ignore_permissions=True)

    # Create admin user with CAPS Admin role
    admin = frappe.get_doc({
        "doctype": "User",
        "email": _USERS["admin"],
        "first_name": "ImpAdmin",
        "send_welcome_email": 0,
        "roles": [{"role": "System Manager"}, {"role": "CAPS Admin"}],
    })
    admin.insert(ignore_permissions=True)

    # Create target user
    target = frappe.get_doc({
        "doctype": "User",
        "email": _USERS["target"],
        "first_name": "ImpTarget",
        "send_welcome_email": 0,
        "roles": [{"role": "System Manager"}],
    })
    target.insert(ignore_permissions=True)

    # Assign admin_only + shared to admin
    frappe.get_doc({
        "doctype": "User Capability",
        "user": _USERS["admin"],
        "direct_capabilities": [
            {"capability": _CAPS["admin_only"]},
            {"capability": _CAPS["shared"]},
        ],
    }).insert(ignore_permissions=True)

    # Assign target_only + shared to target
    frappe.get_doc({
        "doctype": "User Capability",
        "user": _USERS["target"],
        "direct_capabilities": [
            {"capability": _CAPS["target_only"]},
            {"capability": _CAPS["shared"]},
        ],
    }).insert(ignore_permissions=True)

    frappe.db.commit()
    _flush(_USERS["admin"])
    _flush(_USERS["target"])


def _teardown_impersonation_data():
    # Clean impersonation state
    for email in _USERS.values():
        frappe.cache.delete_value(f"caps:impersonate:{email}")

    # Clean audit logs
    frappe.db.sql(
        "DELETE FROM `tabCAPS Audit Log` WHERE capability LIKE %s OR user LIKE %s",
        (f"{_TEST_PREFIX}%", f"{_TEST_PREFIX}%"),
    )

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

    for name in frappe.get_all(
        "Capability",
        filters={"name1": ("like", f"{_TEST_PREFIX}%")},
        pluck="name",
    ):
        frappe.delete_doc("Capability", name, force=True, ignore_permissions=True)

    for email in _USERS.values():
        _safe_delete_user(email)

    frappe.db.commit()


def _safe_delete_user(email):
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


class TestImpersonation(unittest.TestCase):
    """Test CAPS Impersonation functionality."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        _setup_impersonation_data()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        # Make sure we stop any impersonation
        for email in _USERS.values():
            frappe.cache.delete_value(f"caps:impersonate:{email}")
        _teardown_impersonation_data()

    def setUp(self):
        frappe.set_user("Administrator")
        # Clean impersonation state before each test
        for email in _USERS.values():
            frappe.cache.delete_value(f"caps:impersonate:{email}")
            _flush(email)

    def tearDown(self):
        frappe.set_user("Administrator")
        for email in _USERS.values():
            frappe.cache.delete_value(f"caps:impersonate:{email}")
            _flush(email)

    # ─── start_impersonation ───────────────────────────────────────

    def test_start_impersonation(self):
        """start_impersonation should activate impersonation state."""
        from caps.api_impersonation import start_impersonation

        frappe.set_user(_USERS["admin"])
        result = start_impersonation(target_user=_USERS["target"])
        self.assertEqual(result["status"], "active")
        self.assertEqual(result["target_user"], _USERS["target"])

    def test_start_impersonation_self_throws(self):
        """Cannot impersonate yourself."""
        from caps.api_impersonation import start_impersonation

        frappe.set_user(_USERS["admin"])
        with self.assertRaises(Exception):
            start_impersonation(target_user=_USERS["admin"])

    def test_start_impersonation_nonexistent_user_throws(self):
        """Cannot impersonate a non-existent user."""
        from caps.api_impersonation import start_impersonation

        frappe.set_user(_USERS["admin"])
        with self.assertRaises(Exception):
            start_impersonation(target_user="nobody@nowhere.test")

    def test_start_impersonation_double_throws(self):
        """Cannot start impersonation while already impersonating."""
        from caps.api_impersonation import start_impersonation

        frappe.set_user(_USERS["admin"])
        start_impersonation(target_user=_USERS["target"])
        with self.assertRaises(Exception):
            start_impersonation(target_user=_USERS["target"])

    # ─── stop_impersonation ────────────────────────────────────────

    def test_stop_impersonation(self):
        """stop_impersonation should clear impersonation state."""
        from caps.api_impersonation import start_impersonation, stop_impersonation

        frappe.set_user(_USERS["admin"])
        start_impersonation(target_user=_USERS["target"])
        result = stop_impersonation()
        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["was_impersonating"], _USERS["target"])

    def test_stop_when_not_active(self):
        """stop_impersonation when not active should return not_active."""
        from caps.api_impersonation import stop_impersonation

        frappe.set_user(_USERS["admin"])
        result = stop_impersonation()
        self.assertEqual(result["status"], "not_active")

    # ─── get_impersonation_status ──────────────────────────────────

    def test_status_when_active(self):
        """get_impersonation_status should return active state."""
        from caps.api_impersonation import start_impersonation, get_impersonation_status

        frappe.set_user(_USERS["admin"])
        start_impersonation(target_user=_USERS["target"])
        status = get_impersonation_status()
        self.assertTrue(status["active"])
        self.assertEqual(status["target_user"], _USERS["target"])

    def test_status_when_inactive(self):
        """get_impersonation_status should return inactive state."""
        from caps.api_impersonation import get_impersonation_status

        frappe.set_user(_USERS["admin"])
        status = get_impersonation_status()
        self.assertFalse(status["active"])
        self.assertIsNone(status["target_user"])

    # ─── Resolver Integration ──────────────────────────────────────

    def test_impersonation_changes_resolved_caps(self):
        """While impersonating, resolver should return target's capabilities."""
        from caps.api_impersonation import start_impersonation, stop_impersonation
        from caps.utils.resolver import resolve_capabilities

        frappe.set_user(_USERS["admin"])

        # Before impersonation: admin should have admin_only
        caps_before = resolve_capabilities(_USERS["admin"])
        self.assertIn(_CAPS["admin_only"], caps_before)
        self.assertNotIn(_CAPS["target_only"], caps_before)

        # Start impersonation
        start_impersonation(target_user=_USERS["target"])
        _flush(_USERS["admin"])

        # During impersonation: should see target's caps
        caps_during = resolve_capabilities(_USERS["admin"])
        self.assertIn(_CAPS["target_only"], caps_during)
        self.assertNotIn(_CAPS["admin_only"], caps_during)

        # Stop impersonation
        stop_impersonation()
        _flush(_USERS["admin"])

        # After: back to admin's own caps
        caps_after = resolve_capabilities(_USERS["admin"])
        self.assertIn(_CAPS["admin_only"], caps_after)
        self.assertNotIn(_CAPS["target_only"], caps_after)

    # ─── Audit Trail ──────────────────────────────────────────────

    def test_impersonation_creates_audit_logs(self):
        """Impersonation start/stop should create audit log entries."""
        from caps.api_impersonation import start_impersonation, stop_impersonation

        frappe.set_user(_USERS["admin"])
        start_impersonation(target_user=_USERS["target"])
        stop_impersonation()

        logs = frappe.get_all(
            "CAPS Audit Log",
            filters={
                "user": _USERS["admin"],
                "action": ("in", ["impersonation_start", "impersonation_end"]),
            },
            fields=["action", "target_user"],
        )
        actions = [l["action"] for l in logs]
        self.assertIn("impersonation_start", actions)
        self.assertIn("impersonation_end", actions)
