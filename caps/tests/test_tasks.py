"""
CAPS — Scheduled Tasks Tests
================================

Tests for caps.tasks: expire_timeboxed_capabilities,
sync_permission_groups, cleanup_audit_logs.

Run with:
    bench --site dev.localhost run-tests --app caps \
        --module caps.tests.test_tasks
"""

import frappe
import unittest
from frappe.utils import now_datetime, add_days

_TEST_PREFIX = "capstest_task_"

_CAP_NAMES = [
    f"{_TEST_PREFIX}cap:a",
    f"{_TEST_PREFIX}cap:b",
]

_BUNDLE_NAME = f"{_TEST_PREFIX}bundle"

_USERS = {
    "expiring": f"{_TEST_PREFIX}expiring@test.local",
    "permanent": f"{_TEST_PREFIX}permanent@test.local",
}


def _setup_task_data():
    _teardown_task_data()

    for cap_name in _CAP_NAMES:
        frappe.get_doc({
            "doctype": "Capability",
            "name1": cap_name,
            "label": cap_name,
            "category": "Custom",
            "is_active": 1,
        }).insert(ignore_permissions=True)

    # Bundle
    frappe.get_doc({
        "doctype": "Capability Bundle",
        "__newname": _BUNDLE_NAME,
        "label": _BUNDLE_NAME,
        "capabilities": [{"capability": f"{_TEST_PREFIX}cap:b"}],
    }).insert(ignore_permissions=True)

    for key, email in _USERS.items():
        if not frappe.db.exists("User", email):
            frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": "CAPSTask",
                "last_name": key,
                "send_welcome_email": 0,
                "user_type": "System User",
            }).insert(ignore_permissions=True)

    # Expiring user: cap:a expired yesterday, bundle expired yesterday
    frappe.get_doc({
        "doctype": "User Capability",
        "user": _USERS["expiring"],
        "direct_capabilities": [{
            "capability": f"{_TEST_PREFIX}cap:a",
            "expires_on": add_days(now_datetime(), -1),
        }],
        "direct_bundles": [{
            "bundle": _BUNDLE_NAME,
            "expires_on": add_days(now_datetime(), -1),
        }],
    }).insert(ignore_permissions=True)

    # Permanent user: cap:a no expiry
    frappe.get_doc({
        "doctype": "User Capability",
        "user": _USERS["permanent"],
        "direct_capabilities": [{
            "capability": f"{_TEST_PREFIX}cap:a",
        }],
    }).insert(ignore_permissions=True)

    frappe.db.commit()


def _teardown_task_data():
    for email in _USERS.values():
        frappe.cache.delete_value(f"caps:user:{email}")
        if frappe.db.exists("User Capability", email):
            frappe.delete_doc("User Capability", email,
                              force=True, ignore_permissions=True)

    for name in frappe.get_all("Capability Bundle",
                               filters={"label": _BUNDLE_NAME}, pluck="name"):
        frappe.delete_doc("Capability Bundle", name,
                          force=True, ignore_permissions=True)

    for cap_name in _CAP_NAMES:
        if frappe.db.exists("Capability", cap_name):
            frappe.delete_doc("Capability", cap_name,
                              force=True, ignore_permissions=True)

    for email in _USERS.values():
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email,
                              force=True, ignore_permissions=True)

    # Clean audit logs from tests
    frappe.db.delete("CAPS Audit Log", {
        "target_user": ("like", f"{_TEST_PREFIX}%"),
    })

    frappe.db.commit()


# ── Tests ─────────────────────────────────────────────────────────────


class TestExpireTimeboxed(unittest.TestCase):
    """Tests for expire_timeboxed_capabilities task."""

    @classmethod
    def setUpClass(cls):
        _setup_task_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_task_data()

    def test_expired_cap_removed(self):
        """Expired direct capability should be removed."""
        from caps.tasks import expire_timeboxed_capabilities

        # Ensure the expired cap exists (may have been removed by previous test)
        existing = frappe.get_all(
            "User Capability Item",
            filters={"parent": _USERS["expiring"],
                     "capability": f"{_TEST_PREFIX}cap:a"},
        )
        if not existing:
            doc = frappe.get_doc("User Capability", _USERS["expiring"])
            doc.append("direct_capabilities", {
                "capability": f"{_TEST_PREFIX}cap:a",
                "expires_on": add_days(now_datetime(), -1),
            })
            doc.save(ignore_permissions=True)
            frappe.db.commit()

        expire_timeboxed_capabilities()

        remaining = frappe.get_all(
            "User Capability Item",
            filters={
                "parent": _USERS["expiring"],
                "capability": f"{_TEST_PREFIX}cap:a",
            },
        )
        self.assertEqual(len(remaining), 0)

    def test_expired_bundle_removed(self):
        """Expired direct bundle should be removed."""
        from caps.tasks import expire_timeboxed_capabilities

        expire_timeboxed_capabilities()

        remaining = frappe.get_all(
            "User Capability Bundle",
            filters={
                "parent": _USERS["expiring"],
                "bundle": _BUNDLE_NAME,
            },
        )
        self.assertEqual(len(remaining), 0)

    def test_permanent_cap_not_removed(self):
        """Capability without expires_on should NOT be removed."""
        from caps.tasks import expire_timeboxed_capabilities

        expire_timeboxed_capabilities()

        remaining = frappe.get_all(
            "User Capability Item",
            filters={
                "parent": _USERS["permanent"],
                "capability": f"{_TEST_PREFIX}cap:a",
            },
        )
        self.assertEqual(len(remaining), 1)

    def test_expiry_creates_audit_log(self):
        """Expiry should log to CAPS Audit Log."""
        # Re-create expired data for audit test
        existing = frappe.get_all(
            "User Capability Item",
            filters={"parent": _USERS["expiring"],
                     "capability": f"{_TEST_PREFIX}cap:a"},
        )
        if not existing:
            doc = frappe.get_doc("User Capability", _USERS["expiring"])
            doc.append("direct_capabilities", {
                "capability": f"{_TEST_PREFIX}cap:a",
                "expires_on": add_days(now_datetime(), -1),
            })
            doc.save(ignore_permissions=True)
            frappe.db.commit()

        # Clear old audit logs for this test
        frappe.db.delete("CAPS Audit Log", {
            "target_user": _USERS["expiring"],
            "capability": f"{_TEST_PREFIX}cap:a",
        })
        frappe.db.commit()

        from caps.tasks import expire_timeboxed_capabilities
        expire_timeboxed_capabilities()

        logs = frappe.get_all("CAPS Audit Log", filters={
            "target_user": _USERS["expiring"],
            "action": "capability_revoked",
            "capability": f"{_TEST_PREFIX}cap:a",
        })
        self.assertGreater(len(logs), 0)

    def test_expiry_invalidates_cache(self):
        """After expiry, user's cache should be invalidated."""
        from caps.utils.resolver import resolve_capabilities
        user = _USERS["expiring"]

        # Re-add expired cap
        if not frappe.get_all("User Capability Item", filters={
            "parent": user, "capability": f"{_TEST_PREFIX}cap:a",
        }):
            doc = frappe.get_doc("User Capability", user)
            doc.append("direct_capabilities", {
                "capability": f"{_TEST_PREFIX}cap:a",
                "expires_on": add_days(now_datetime(), -1),
            })
            doc.save(ignore_permissions=True)
            frappe.db.commit()

        # Populate cache
        frappe.cache.delete_value(f"caps:user:{user}")
        resolve_capabilities(user)
        self.assertIsNotNone(frappe.cache.get_value(f"caps:user:{user}"))

        from caps.tasks import expire_timeboxed_capabilities
        expire_timeboxed_capabilities()

        self.assertIsNone(frappe.cache.get_value(f"caps:user:{user}"))


class TestCleanupAuditLogs(unittest.TestCase):
    """Tests for cleanup_audit_logs task."""

    def test_old_logs_deleted(self):
        """Audit logs older than 90 days should be deleted."""
        # Create an old log
        old_name = frappe.get_doc({
            "doctype": "CAPS Audit Log",
            "user": "Administrator",
            "action": "capability_check",
            "capability": f"{_TEST_PREFIX}old_cap",
            "result": "denied",
            "timestamp": add_days(now_datetime(), -100),
        }).insert(ignore_permissions=True).name
        frappe.db.commit()

        from caps.tasks import cleanup_audit_logs
        cleanup_audit_logs()

        self.assertFalse(frappe.db.exists("CAPS Audit Log", old_name))

    def test_recent_logs_kept(self):
        """Audit logs newer than 90 days should NOT be deleted."""
        recent_name = frappe.get_doc({
            "doctype": "CAPS Audit Log",
            "user": "Administrator",
            "action": "capability_check",
            "capability": f"{_TEST_PREFIX}recent_cap",
            "result": "denied",
            "timestamp": add_days(now_datetime(), -10),
        }).insert(ignore_permissions=True).name
        frappe.db.commit()

        from caps.tasks import cleanup_audit_logs
        cleanup_audit_logs()

        self.assertTrue(frappe.db.exists("CAPS Audit Log", recent_name))

        # Cleanup
        frappe.delete_doc("CAPS Audit Log", recent_name,
                          force=True, ignore_permissions=True)
