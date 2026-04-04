# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS — Hooks Integration Tests
================================

Tests for hooks_integration.py:
 - auto_filter_fields (wildcard on_load)
 - auto_validate_writes (wildcard before_save)
 - on_login_audit

Prefix: capstest_hki_

Run with:
    bench --site dev.localhost run-tests --app caps \
        --module caps.tests.test_hooks_integration
"""

import frappe
import unittest

_TEST_PREFIX = "capstest_hki_"

_CAPS = {
    "field": f"{_TEST_PREFIX}cap:viewphone",
}

_USERS = {
    "limited": f"{_TEST_PREFIX}limited@test.local",
}


def _setup_hooks_data():
    _teardown_hooks_data()

    # Create capability
    frappe.get_doc({
        "doctype": "Capability",
        "name1": _CAPS["field"],
        "label": "View Phone",
        "category": "Field",
        "is_active": 1,
    }).insert(ignore_permissions=True)

    # Create a field map: restrict "phone" on ToDo unless user has cap
    frappe.get_doc({
        "doctype": "Field Capability Map",
        "doctype_name": "ToDo",
        "fieldname": "description",
        "capability": _CAPS["field"],
        "behavior": "hide",
    }).insert(ignore_permissions=True)

    # Create limited user WITHOUT the capability
    user = frappe.get_doc({
        "doctype": "User",
        "email": _USERS["limited"],
        "first_name": "HkiLimited",
        "send_welcome_email": 0,
        "roles": [{"role": "System Manager"}],
    })
    user.insert(ignore_permissions=True)

    # NO User Capability doc → user has no capabilities
    frappe.db.commit()
    _flush(_USERS["limited"])


def _teardown_hooks_data():
    # Clean audit logs
    frappe.db.sql(
        "DELETE FROM `tabCAPS Audit Log` WHERE user LIKE %s OR capability LIKE %s",
        (f"{_TEST_PREFIX}%", f"{_TEST_PREFIX}%"),
    )

    # Clean field maps
    for name in frappe.get_all(
        "Field Capability Map",
        filters={"capability": ("like", f"{_TEST_PREFIX}%")},
        pluck="name",
    ):
        frappe.delete_doc("Field Capability Map", name, force=True, ignore_permissions=True)

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
    frappe.cache.delete_value("caps:fieldmap:ToDo")
    frappe.cache.delete_value("caps:actionmap:ToDo")


def _clear_settings_cache():
    if hasattr(frappe.local, "_caps_settings"):
        del frappe.local._caps_settings
    frappe.clear_document_cache("CAPS Settings", "CAPS Settings")


class TestHooksIntegration(unittest.TestCase):
    """Test CAPS auto doc-event hooks."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        _setup_hooks_data()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        _teardown_hooks_data()

    def setUp(self):
        frappe.set_user("Administrator")
        _clear_settings_cache()

    # ─── auto_filter_fields ────────────────────────────────────────

    def test_auto_filter_hides_restricted_field(self):
        """auto_filter_fields should hide restricted fields on load."""
        from caps.hooks_integration import auto_filter_fields

        # Create a ToDo
        todo = frappe.get_doc({
            "doctype": "ToDo",
            "description": "Secret description content",
        })
        todo.insert(ignore_permissions=True)
        frappe.db.commit()

        try:
            # As limited user, filter should hide description
            frappe.set_user(_USERS["limited"])
            _flush(_USERS["limited"])

            doc = frappe.get_doc("ToDo", todo.name)
            auto_filter_fields(doc)

            # Description should be None (hidden)
            self.assertIsNone(doc.description)
        finally:
            frappe.set_user("Administrator")
            frappe.delete_doc("ToDo", todo.name, force=True, ignore_permissions=True)

    def test_auto_filter_skips_admin(self):
        """auto_filter_fields should not filter for Administrator."""
        from caps.hooks_integration import auto_filter_fields

        todo = frappe.get_doc({
            "doctype": "ToDo",
            "description": "Admin sees all",
        })
        todo.insert(ignore_permissions=True)
        frappe.db.commit()

        try:
            doc = frappe.get_doc("ToDo", todo.name)
            auto_filter_fields(doc)
            # Admin should still see description
            self.assertEqual(doc.description, "Admin sees all")
        finally:
            frappe.delete_doc("ToDo", todo.name, force=True, ignore_permissions=True)

    def test_auto_filter_skips_unrestricted_doctype(self):
        """auto_filter_fields should not filter doctypes without field maps."""
        from caps.hooks_integration import auto_filter_fields

        # Note doctype has no field maps
        note = frappe.get_doc({
            "doctype": "Note",
            "title": f"{_TEST_PREFIX}test_note",
            "content": "Visible content",
        })
        note.insert(ignore_permissions=True)
        frappe.db.commit()

        try:
            frappe.set_user(_USERS["limited"])
            _flush(_USERS["limited"])
            doc = frappe.get_doc("Note", note.name)
            auto_filter_fields(doc)
            # Content should be unchanged (no restriction on Note)
            self.assertEqual(doc.content, "Visible content")
        finally:
            frappe.set_user("Administrator")
            frappe.delete_doc("Note", note.name, force=True, ignore_permissions=True)

    # ─── auto_validate_writes ──────────────────────────────────────

    def test_auto_validate_blocks_restricted_write(self):
        """auto_validate_writes should block writes to restricted fields."""
        from caps.hooks_integration import auto_validate_writes

        todo = frappe.get_doc({
            "doctype": "ToDo",
            "description": "Original",
        })
        todo.insert(ignore_permissions=True)
        frappe.db.commit()

        try:
            frappe.set_user(_USERS["limited"])
            _flush(_USERS["limited"])

            doc = frappe.get_doc("ToDo", todo.name)
            # Simulate Frappe's before_save state: _doc_before_save is set by get_doc_before_save()
            doc._doc_before_save = frappe.get_doc("ToDo", todo.name)
            doc.description = "Modified"
            doc.flags.ignore_validate = True

            # Behavior is "hide", so writing should be blocked
            with self.assertRaises(frappe.PermissionError):
                auto_validate_writes(doc)
        finally:
            frappe.set_user("Administrator")
            frappe.delete_doc("ToDo", todo.name, force=True, ignore_permissions=True)

    # ─── should_enforce toggle ─────────────────────────────────────

    def test_disabled_caps_skips_enforcement(self):
        """When CAPS is disabled, auto hooks should be no-ops."""
        from caps.hooks_integration import auto_filter_fields

        frappe.db.set_single_value("CAPS Settings", "enable_caps", 0)
        _clear_settings_cache()

        todo = frappe.get_doc({
            "doctype": "ToDo",
            "description": "Should remain",
        })
        todo.insert(ignore_permissions=True)
        frappe.db.commit()

        try:
            frappe.set_user(_USERS["limited"])
            _flush(_USERS["limited"])

            doc = frappe.get_doc("ToDo", todo.name)
            auto_filter_fields(doc)
            # CAPS disabled → no filtering
            self.assertEqual(doc.description, "Should remain")
        finally:
            frappe.set_user("Administrator")
            frappe.db.set_single_value("CAPS Settings", "enable_caps", 1)
            _clear_settings_cache()
            frappe.delete_doc("ToDo", todo.name, force=True, ignore_permissions=True)

    # ─── on_login_audit ────────────────────────────────────────────

    def test_login_audit_creates_log(self):
        """on_login_audit should create an audit log entry."""
        from caps.hooks_integration import on_login_audit

        class MockLoginManager:
            user = _USERS["limited"]

        on_login_audit(MockLoginManager())

        logs = frappe.get_all(
            "CAPS Audit Log",
            filters={
                "user": _USERS["limited"],
                "capability": ("like", "login:%"),
            },
            pluck="capability",
        )
        self.assertTrue(any("login:count=" in l for l in logs))
