"""
CAPS — Phase 11 Tests: Expiry Notifications
=============================================

Tests for the warn_expiring_capabilities daily task,
notification creation, and the settings toggle.

Run with:
    bench --site dev.localhost run-tests --app caps \
        --module caps.tests.test_expiry_notifications
"""

import frappe
import unittest
from datetime import datetime, timedelta

_P = "capstest_exp_"

_CAPS = {
    "a": f"{_P}cap:alpha",
    "b": f"{_P}cap:bravo",
}

_BUNDLES = {
    "x": f"{_P}bun:xray",
}

_USERS = {
    "u1": f"{_P}u1@test.local",
}


def _setup():
    _teardown()

    for key, name in _CAPS.items():
        frappe.get_doc({
            "doctype": "Capability",
            "name1": name,
            "label": name,
            "category": "Custom",
            "is_active": 1,
        }).insert(ignore_permissions=True)

    frappe.get_doc({
        "doctype": "Capability Bundle",
        "__newname": _BUNDLES["x"],
        "label": _BUNDLES["x"],
        "capabilities": [{"capability": _CAPS["a"]}],
    }).insert(ignore_permissions=True)

    for key, email in _USERS.items():
        if not frappe.db.exists("User", email):
            frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": "CAPSExp",
                "last_name": key,
                "send_welcome_email": 0,
                "user_type": "System User",
            }).insert(ignore_permissions=True)

    frappe.db.commit()


def _teardown():
    from caps.utils.resolver import invalidate_all_caches
    invalidate_all_caches()

    for email in _USERS.values():
        if frappe.db.exists("User Capability", email):
            frappe.delete_doc("User Capability", email, force=True)

    for name in _BUNDLES.values():
        if frappe.db.exists("Capability Bundle", name):
            frappe.delete_doc("Capability Bundle", name, force=True)

    for name in _CAPS.values():
        if frappe.db.exists("Capability", name):
            frappe.delete_doc("Capability", name, force=True)

    for email in _USERS.values():
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True)

    # Clean up notifications
    frappe.db.delete("Notification Log", {
        "subject": ["like", "%CAPS%expir%"]
    })

    frappe.db.commit()


class TestExpiryNotifications(unittest.TestCase):
    """Test warn_expiring_capabilities scheduled task."""

    @classmethod
    def setUpClass(cls):
        _setup()

    @classmethod
    def tearDownClass(cls):
        _teardown()

    def setUp(self):
        if frappe.db.exists("User Capability", _USERS["u1"]):
            frappe.delete_doc("User Capability", _USERS["u1"], force=True)
        frappe.db.delete("Notification Log", {
            "subject": ["like", "%CAPS%expir%"]
        })
        frappe.db.commit()
        # Clear settings cache so tests see fresh values
        if hasattr(frappe.local, "_caps_settings"):
            del frappe.local._caps_settings
        frappe.clear_cache(doctype="CAPS Settings")
        from caps.utils.resolver import invalidate_all_caches
        invalidate_all_caches()

    def _grant_with_expiry(self, cap_name, days_from_now):
        """Helper to grant a capability with an expiry date."""
        user = _USERS["u1"]
        if not frappe.db.exists("User Capability", user):
            frappe.get_doc({"doctype": "User Capability", "user": user}).insert(ignore_permissions=True)
        doc = frappe.get_doc("User Capability", user)
        doc.append("direct_capabilities", {
            "capability": cap_name,
            "expires_on": datetime.now() + timedelta(days=days_from_now),
        })
        doc.save(ignore_permissions=True)
        frappe.db.commit()

    def _grant_bundle_with_expiry(self, bundle_name, days_from_now):
        """Helper to grant a bundle with an expiry date."""
        user = _USERS["u1"]
        if not frappe.db.exists("User Capability", user):
            frappe.get_doc({"doctype": "User Capability", "user": user}).insert(ignore_permissions=True)
        doc = frappe.get_doc("User Capability", user)
        doc.append("direct_bundles", {
            "bundle": bundle_name,
            "expires_on": datetime.now() + timedelta(days=days_from_now),
        })
        doc.save(ignore_permissions=True)
        frappe.db.commit()

    def test_expiring_cap_creates_notification(self):
        """Capability expiring within window creates notification."""
        self._grant_with_expiry(_CAPS["a"], 3)  # Expires in 3 days, default window = 7

        from caps.tasks import warn_expiring_capabilities
        warn_expiring_capabilities()

        notes = frappe.get_all("Notification Log", filters={
            "for_user": _USERS["u1"],
            "subject": ["like", "%CAPS%expir%"],
        })
        self.assertTrue(len(notes) > 0, "Should create expiry notification")

    def test_far_future_no_notification(self):
        """Capability expiring far in the future does NOT create notification."""
        self._grant_with_expiry(_CAPS["a"], 30)  # 30 days out, window = 7

        from caps.tasks import warn_expiring_capabilities
        warn_expiring_capabilities()

        notes = frappe.get_all("Notification Log", filters={
            "for_user": _USERS["u1"],
            "subject": ["like", "%CAPS%expir%"],
        })
        self.assertEqual(len(notes), 0, "Should NOT create notification for far future expiry")

    def test_already_expired_no_notification(self):
        """Already-expired capability does NOT trigger expiry warning."""
        self._grant_with_expiry(_CAPS["a"], -2)  # Expired 2 days ago

        from caps.tasks import warn_expiring_capabilities
        warn_expiring_capabilities()

        notes = frappe.get_all("Notification Log", filters={
            "for_user": _USERS["u1"],
            "subject": ["like", "%CAPS%expir%"],
        })
        self.assertEqual(len(notes), 0, "Should NOT notify for already-expired caps")

    def test_bundle_expiring_creates_notification(self):
        """Bundle expiring within window creates notification."""
        self._grant_bundle_with_expiry(_BUNDLES["x"], 5)

        from caps.tasks import warn_expiring_capabilities
        warn_expiring_capabilities()

        notes = frappe.get_all("Notification Log", filters={
            "for_user": _USERS["u1"],
            "subject": ["like", "%CAPS%expir%"],
        })
        self.assertTrue(len(notes) > 0, "Should create expiry notification for bundle")

    def test_disabled_notifications_skipped(self):
        """When enable_expiry_notifications is off, no notifications sent."""
        self._grant_with_expiry(_CAPS["a"], 3)

        # Disable notifications
        settings = frappe.get_doc("CAPS Settings")
        original = settings.enable_expiry_notifications
        settings.enable_expiry_notifications = 0
        settings.save(ignore_permissions=True)
        frappe.db.commit()
        # Clear settings cache so task sees fresh value
        if hasattr(frappe.local, "_caps_settings"):
            del frappe.local._caps_settings
        frappe.clear_cache(doctype="CAPS Settings")

        try:
            from caps.tasks import warn_expiring_capabilities
            warn_expiring_capabilities()

            notes = frappe.get_all("Notification Log", filters={
                "for_user": _USERS["u1"],
                "subject": ["like", "%CAPS%expir%"],
            })
            self.assertEqual(len(notes), 0, "Should NOT notify when disabled")
        finally:
            settings.enable_expiry_notifications = original or 1
            settings.save(ignore_permissions=True)
            frappe.db.commit()
            if hasattr(frappe.local, "_caps_settings"):
                del frappe.local._caps_settings
            frappe.clear_cache(doctype="CAPS Settings")

    def test_custom_warning_days(self):
        """Respects custom expiry_warning_days setting."""
        self._grant_with_expiry(_CAPS["a"], 3)  # 3 days out

        settings = frappe.get_doc("CAPS Settings")
        original = settings.expiry_warning_days
        settings.expiry_warning_days = 2  # Window is only 2 days
        settings.save(ignore_permissions=True)
        frappe.db.commit()
        # Clear settings cache so task sees fresh value
        if hasattr(frappe.local, "_caps_settings"):
            del frappe.local._caps_settings
        frappe.clear_cache(doctype="CAPS Settings")

        try:
            from caps.tasks import warn_expiring_capabilities
            warn_expiring_capabilities()

            notes = frappe.get_all("Notification Log", filters={
                "for_user": _USERS["u1"],
                "subject": ["like", "%CAPS%expir%"],
            })
            self.assertEqual(len(notes), 0, "3-day expiry outside 2-day window → no notification")
        finally:
            settings.expiry_warning_days = original or 7
            settings.save(ignore_permissions=True)
            frappe.db.commit()
            if hasattr(frappe.local, "_caps_settings"):
                del frappe.local._caps_settings
            frappe.clear_cache(doctype="CAPS Settings")
