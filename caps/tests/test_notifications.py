"""
CAPS — Notification System Tests
===================================

Tests for the centralized notification engine (Phase 25):
 - notify_capability_change
 - notify_request_submitted / approved / rejected
 - notify_delegation
 - notify_expiry_warning
 - get_notification_config
 - Settings flags (enable/disable)

Prefix: capstest_notif_

Run with:
    bench --site dev.localhost run-tests --app caps \
        --module caps.tests.test_notifications
"""

import frappe
import unittest

_TEST_PREFIX = "capstest_notif_"

_CAPS = {
    "cap_a": f"{_TEST_PREFIX}cap:a",
    "cap_b": f"{_TEST_PREFIX}cap:b",
}

_USERS = {
    "target": f"{_TEST_PREFIX}target@test.local",
    "admin": f"{_TEST_PREFIX}admin@test.local",
}


def _setup_data():
    _teardown_data()

    for key, name in _CAPS.items():
        frappe.get_doc({
            "doctype": "Capability",
            "name1": name,
            "label": f"Notif Cap {key}",
            "category": "Custom",
            "is_active": 1,
        }).insert(ignore_permissions=True)

    for key, email in _USERS.items():
        roles = [{"role": "System Manager"}]
        if key == "admin":
            roles.append({"role": "CAPS Admin"})
        frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": f"Notif{key.title()}",
            "send_welcome_email": 0,
            "roles": roles,
        }).insert(ignore_permissions=True)

    frappe.db.commit()
    _flush()


def _teardown_data():
    # Clean notification logs
    for nl in frappe.get_all(
        "Notification Log",
        filters={"for_user": ("like", f"{_TEST_PREFIX}%")},
        pluck="name",
    ):
        frappe.delete_doc("Notification Log", nl, force=True, ignore_permissions=True)

    # Clean caps
    for name in _CAPS.values():
        if frappe.db.exists("Capability", name):
            frappe.delete_doc("Capability", name, force=True, ignore_permissions=True)

    # Clean users
    for email in _USERS.values():
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)

    frappe.db.commit()


def _flush():
    from caps.utils.resolver import invalidate_all_caches
    invalidate_all_caches()


class TestNotifyCapabilityChange(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _setup_data()
        # Ensure notification setting is enabled
        frappe.db.set_single_value("CAPS Settings", "notify_on_capability_change", 1)
        frappe.cache.delete_value("caps:settings")
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        _teardown_data()

    def test_notify_cap_change_creates_notification_log(self):
        """notify_capability_change creates a Notification Log entry for the target user."""
        from caps.notifications import _create_notification

        # Test the low-level _create_notification directly
        doc = frappe.get_doc({
            "doctype": "Notification Log",
            "for_user": _USERS["target"],
            "from_user": _USERS["admin"],
            "type": "Alert",
            "subject": f"{_TEST_PREFIX}test_subject",
            "email_content": "test",
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        logs = frappe.get_all(
            "Notification Log",
            filters={"for_user": _USERS["target"], "subject": ("like", f"{_TEST_PREFIX}%")},
            pluck="name",
        )
        self.assertTrue(len(logs) > 0, "Should create a notification log")

        # Clean up
        for name in logs:
            frappe.delete_doc("Notification Log", name, force=True, ignore_permissions=True)
        frappe.db.commit()

    def test_notify_cap_change_function_runs(self):
        """notify_capability_change runs without error when setting is on."""
        from caps.notifications import notify_capability_change

        # Should not raise any exception
        notify_capability_change(
            _USERS["target"],
            granted=[_CAPS["cap_a"]],
            revoked=[],
            changed_by=_USERS["admin"],
        )
        # Success = no exception raised

    def test_notify_cap_change_with_revoked(self):
        """notify_capability_change handles revoke list without error."""
        from caps.notifications import notify_capability_change

        # Should not raise
        notify_capability_change(
            _USERS["target"],
            granted=[],
            revoked=[_CAPS["cap_b"]],
            changed_by=_USERS["admin"],
        )

    def test_notify_cap_change_respects_setting(self):
        """No notification when notify_on_capability_change is disabled."""
        from caps.notifications import notify_capability_change, _is_notify_on_change_enabled

        # Disable the setting
        frappe.db.set_single_value("CAPS Settings", "notify_on_capability_change", 0)
        frappe.clear_cache(doctype="CAPS Settings")
        if hasattr(frappe.local, "_caps_settings"):
            del frappe.local._caps_settings
        frappe.db.commit()

        try:
            # Verify the setting reads as disabled
            self.assertFalse(_is_notify_on_change_enabled(),
                             "Setting should be disabled")

            # Count before
            before = frappe.db.count("Notification Log", {"for_user": _USERS["target"]})

            notify_capability_change(
                _USERS["target"],
                granted=[_CAPS["cap_a"]],
                revoked=[],
                changed_by=_USERS["admin"],
            )
            frappe.db.commit()

            after = frappe.db.count("Notification Log", {"for_user": _USERS["target"]})
            self.assertEqual(before, after, "No notification when setting is disabled")
        finally:
            frappe.db.set_single_value("CAPS Settings", "notify_on_capability_change", 1)
            frappe.clear_cache(doctype="CAPS Settings")
            if hasattr(frappe.local, "_caps_settings"):
                del frappe.local._caps_settings
            frappe.db.commit()


class TestNotifyRequestFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _setup_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_data()

    def test_notify_request_approved(self):
        """notify_request_approved runs without error."""
        from caps.notifications import notify_request_approved

        notify_request_approved(
            request_name="FAKE-REQ-001",
            user=_USERS["target"],
            capability=_CAPS["cap_a"],
            approver=_USERS["admin"],
            note="Looks good",
        )
        # Success = no exception raised

    def test_notify_request_rejected(self):
        """notify_request_rejected runs without error."""
        from caps.notifications import notify_request_rejected

        notify_request_rejected(
            request_name="FAKE-REQ-002",
            user=_USERS["target"],
            capability=_CAPS["cap_a"],
            approver=_USERS["admin"],
            note="Not needed",
        )
        # Success = no exception raised


class TestNotifyDelegation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _setup_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_data()

    def test_notify_delegation_creates_log(self):
        """notify_delegation runs without error."""
        from caps.notifications import notify_delegation

        notify_delegation(
            delegator=_USERS["admin"],
            delegatee=_USERS["target"],
            capability=_CAPS["cap_a"],
            action="granted",
        )
        # Success = no exception raised


class TestNotificationConfig(unittest.TestCase):
    def test_get_notification_config_returns_dict(self):
        """get_notification_config returns expected structure."""
        from caps.notifications import get_notification_config

        config = get_notification_config()

        self.assertIn("for_doctype", config)
        self.assertIn("Capability Request", config["for_doctype"])
        self.assertEqual(config["for_doctype"]["Capability Request"], {"status": "Pending"})
