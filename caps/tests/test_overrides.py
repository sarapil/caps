# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS — Overrides Unit Tests
==============================

Comprehensive tests for caps.overrides covering:
- filter_response_fields (hide, read_only, mask behaviours)
- validate_field_write_permissions (block writes to restricted fields)
- check_action_permission (raise on denied actions)
- filter_export_fields (mask/hide in export data)
- _apply_mask (pattern engine)

Run with:
    bench --site dev.localhost run-tests --app caps \
        --module caps.tests.test_overrides
"""

import frappe
import unittest
from frappe.utils import now_datetime

_TEST_PREFIX = "capstest_ovr_"

_CAP_NAMES = [
    f"{_TEST_PREFIX}cap:view_phone",
    f"{_TEST_PREFIX}cap:view_email",
    f"{_TEST_PREFIX}cap:do_approve",
]

_USERS = {
    "has_phone": f"{_TEST_PREFIX}hasphone@test.local",
    "no_caps":   f"{_TEST_PREFIX}nocaps@test.local",
}


def _setup_overrides_data():
    _teardown_overrides_data()

    # Create capabilities
    for cap_name in _CAP_NAMES:
        frappe.get_doc({
            "doctype": "Capability",
            "name1": cap_name,
            "label": cap_name,
            "category": "Custom",
            "is_active": 1,
        }).insert(ignore_permissions=True)

    # Create users
    for key, email in _USERS.items():
        if not frappe.db.exists("User", email):
            frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": "CAPSOvr",
                "last_name": key,
                "send_welcome_email": 0,
                "user_type": "System User",
            }).insert(ignore_permissions=True)

    # Grant view_phone to "has_phone" user
    frappe.get_doc({
        "doctype": "User Capability",
        "user": _USERS["has_phone"],
        "direct_capabilities": [
            {"capability": f"{_TEST_PREFIX}cap:view_phone"},
        ],
    }).insert(ignore_permissions=True)

    # Field maps on Note doctype (clean, no AuraCRM maps)
    frappe.get_doc({
        "doctype": "Field Capability Map",
        "doctype_name": "Note",
        "fieldname": "title",
        "capability": f"{_TEST_PREFIX}cap:view_phone",
        "behavior": "hide",
        "priority": 10,
    }).insert(ignore_permissions=True)

    frappe.get_doc({
        "doctype": "Field Capability Map",
        "doctype_name": "Note",
        "fieldname": "content",
        "capability": f"{_TEST_PREFIX}cap:view_email",
        "behavior": "mask",
        "mask_pattern": "{first2}***",
        "priority": 5,
    }).insert(ignore_permissions=True)

    # Action map
    frappe.get_doc({
        "doctype": "Action Capability Map",
        "doctype_name": "Note",
        "action_id": f"{_TEST_PREFIX}approve",
        "action_type": "button",
        "capability": f"{_TEST_PREFIX}cap:do_approve",
        "fallback_behavior": "hide",
        "fallback_message": "Cannot approve",
    }).insert(ignore_permissions=True)

    frappe.db.commit()
    from caps.utils.resolver import invalidate_field_action_caches
    invalidate_field_action_caches()


def _teardown_overrides_data():
    # Clean maps
    for dt in ("Field Capability Map", "Action Capability Map"):
        for name in frappe.get_all(dt,
                                    filters={"capability": ("like", f"{_TEST_PREFIX}%")},
                                    pluck="name"):
            frappe.delete_doc(dt, name, force=True, ignore_permissions=True)

    # User Capabilities
    for email in _USERS.values():
        if frappe.db.exists("User Capability", email):
            frappe.delete_doc("User Capability", email,
                              force=True, ignore_permissions=True)

    # Capabilities
    for cap_name in _CAP_NAMES:
        if frappe.db.exists("Capability", cap_name):
            frappe.delete_doc("Capability", cap_name,
                              force=True, ignore_permissions=True)

    # Users
    for email in _USERS.values():
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email,
                              force=True, ignore_permissions=True)

    frappe.db.commit()
    from caps.utils.resolver import invalidate_field_action_caches
    invalidate_field_action_caches()


def _flush_user(user):
    frappe.cache.delete_value(f"caps:user:{user}")
    frappe.cache.delete_value("caps:fieldmap:Note")
    frappe.cache.delete_value("caps:actionmap:Note")


# ── Test Classes ──────────────────────────────────────────────────────


class TestFilterResponseFields(unittest.TestCase):
    """Tests for filter_response_fields — hide, read_only, mask."""

    @classmethod
    def setUpClass(cls):
        _setup_overrides_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_overrides_data()

    def _make_mock_doc(self, title="Test Note", content="user@example.com"):
        """Create a real Note doc for testing."""
        doc = frappe.get_doc({
            "doctype": "Note",
            "title": f"{_TEST_PREFIX}{title}_{frappe.generate_hash(length=4)}",
            "content": content,
            "public": 1,
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return doc

    def test_hide_removes_field_value(self):
        """With behavior=hide, filter_response_fields should set field to None."""
        from caps.overrides import filter_response_fields
        doc = self._make_mock_doc(title="HideTest")
        _flush_user(_USERS["no_caps"])
        old_user = frappe.session.user
        frappe.set_user(_USERS["no_caps"])
        try:
            filter_response_fields(doc)
            self.assertIsNone(doc.title)
        finally:
            frappe.set_user(old_user)
            doc.delete(force=True, ignore_permissions=True)

    def test_hide_skipped_when_user_has_cap(self):
        """User with the required cap should keep the field value."""
        from caps.overrides import filter_response_fields
        doc = self._make_mock_doc(title="KeepTest")
        original_title = doc.title
        _flush_user(_USERS["has_phone"])
        old_user = frappe.session.user
        frappe.set_user(_USERS["has_phone"])
        try:
            filter_response_fields(doc)
            self.assertEqual(doc.title, original_title)
        finally:
            frappe.set_user(old_user)
            doc.delete(force=True, ignore_permissions=True)

    def test_mask_applies_pattern(self):
        """With behavior=mask, field should be masked via pattern."""
        from caps.overrides import filter_response_fields
        doc = self._make_mock_doc(title="MaskTest", content="user@example.com")
        _flush_user(_USERS["no_caps"])
        old_user = frappe.session.user
        frappe.set_user(_USERS["no_caps"])
        try:
            filter_response_fields(doc)
            # content has mask pattern "{first2}***" → "us***"
            self.assertEqual(doc.content, "us***")
        finally:
            frappe.set_user(old_user)
            doc.delete(force=True, ignore_permissions=True)

    def test_administrator_no_filtering(self):
        """Administrator should never have fields filtered."""
        from caps.overrides import filter_response_fields
        doc = self._make_mock_doc(title="AdminTest", content="secret")
        original_content = doc.content
        old_user = frappe.session.user
        frappe.set_user("Administrator")
        try:
            filter_response_fields(doc)
            self.assertEqual(doc.content, original_content)
        finally:
            frappe.set_user(old_user)
            doc.delete(force=True, ignore_permissions=True)

    def test_empty_value_not_masked(self):
        """Mask should not be applied to empty values."""
        from caps.overrides import filter_response_fields
        doc = self._make_mock_doc(title="EmptyMask", content="")
        _flush_user(_USERS["no_caps"])
        old_user = frappe.session.user
        frappe.set_user(_USERS["no_caps"])
        try:
            filter_response_fields(doc)
            # content is empty, mask should not run → still empty/None
            # title should be hidden (set to None)
            self.assertIsNone(doc.title)
        finally:
            frappe.set_user(old_user)
            doc.delete(force=True, ignore_permissions=True)


class TestValidateFieldWritePermissions(unittest.TestCase):
    """Tests for validate_field_write_permissions — block writes to restricted fields."""

    @classmethod
    def setUpClass(cls):
        _setup_overrides_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_overrides_data()

    def test_write_blocked_for_hidden_field(self):
        """Changing a hidden field should raise PermissionError."""
        from caps.overrides import validate_field_write_permissions

        # Create and save a Note
        doc = frappe.get_doc({
            "doctype": "Note",
            "title": f"{_TEST_PREFIX}WriteBlock_{frappe.generate_hash(length=4)}",
            "content": "original",
            "public": 1,
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        _flush_user(_USERS["no_caps"])
        old_user = frappe.session.user
        frappe.set_user(_USERS["no_caps"])
        try:
            # Reload to ensure _doc_before_save
            doc.reload()
            doc._doc_before_save = frappe.get_doc("Note", doc.name)
            doc.title = "modified title"
            with self.assertRaises(frappe.PermissionError):
                validate_field_write_permissions(doc)
        finally:
            frappe.set_user(old_user)
            doc.delete(force=True, ignore_permissions=True)

    def test_write_allowed_when_user_has_cap(self):
        """User with the cap should be able to write to the field."""
        from caps.overrides import validate_field_write_permissions

        doc = frappe.get_doc({
            "doctype": "Note",
            "title": f"{_TEST_PREFIX}WriteOK_{frappe.generate_hash(length=4)}",
            "content": "original",
            "public": 1,
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        _flush_user(_USERS["has_phone"])
        old_user = frappe.session.user
        frappe.set_user(_USERS["has_phone"])
        try:
            doc.reload()
            doc._doc_before_save = frappe.get_doc("Note", doc.name)
            doc.title = "modified title"
            # Should NOT raise
            validate_field_write_permissions(doc)
        finally:
            frappe.set_user(old_user)
            doc.delete(force=True, ignore_permissions=True)

    def test_write_allowed_for_new_docs(self):
        """New documents (is_new) should bypass write validation."""
        from caps.overrides import validate_field_write_permissions

        doc = frappe.get_doc({
            "doctype": "Note",
            "title": f"{_TEST_PREFIX}NewDoc_{frappe.generate_hash(length=4)}",
            "content": "new",
            "public": 1,
        })
        _flush_user(_USERS["no_caps"])
        old_user = frappe.session.user
        frappe.set_user(_USERS["no_caps"])
        try:
            # Should NOT raise — doc is new
            validate_field_write_permissions(doc)
        finally:
            frappe.set_user(old_user)

    def test_write_allowed_for_administrator(self):
        """Administrator should always be able to write."""
        from caps.overrides import validate_field_write_permissions

        doc = frappe.get_doc({
            "doctype": "Note",
            "title": f"{_TEST_PREFIX}AdminWrite_{frappe.generate_hash(length=4)}",
            "content": "original",
            "public": 1,
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        old_user = frappe.session.user
        frappe.set_user("Administrator")
        try:
            doc.reload()
            doc._doc_before_save = frappe.get_doc("Note", doc.name)
            doc.title = "admin modified"
            validate_field_write_permissions(doc)
        finally:
            frappe.set_user(old_user)
            doc.delete(force=True, ignore_permissions=True)


class TestCheckActionPermission(unittest.TestCase):
    """Tests for check_action_permission."""

    @classmethod
    def setUpClass(cls):
        _setup_overrides_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_overrides_data()

    def test_action_denied_raises(self):
        """check_action_permission should raise when user lacks the cap."""
        from caps.overrides import check_action_permission
        _flush_user(_USERS["no_caps"])
        with self.assertRaises(frappe.PermissionError):
            check_action_permission("Note", f"{_TEST_PREFIX}approve",
                                    _USERS["no_caps"])

    def test_action_allowed_for_admin(self):
        """Administrator should never be denied."""
        from caps.overrides import check_action_permission
        # Should NOT raise
        check_action_permission("Note", f"{_TEST_PREFIX}approve", "Administrator")

    def test_unregistered_action_allowed(self):
        """An action not registered in Action Capability Map should pass."""
        from caps.overrides import check_action_permission
        _flush_user(_USERS["no_caps"])
        # Should NOT raise — this action doesn't exist in maps
        check_action_permission("Note", "nonexistent_action", _USERS["no_caps"])


class TestFilterExportFields(unittest.TestCase):
    """Tests for filter_export_fields."""

    @classmethod
    def setUpClass(cls):
        _setup_overrides_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_overrides_data()

    def test_hide_in_export(self):
        """Hidden fields should be blanked in export."""
        from caps.overrides import filter_export_fields
        _flush_user(_USERS["no_caps"])
        data = [{"title": "Secret Title", "content": "user@example.com"}]
        result = filter_export_fields("Note", data, _USERS["no_caps"])
        self.assertEqual(result[0]["title"], "")

    def test_mask_in_export(self):
        """Masked fields should be masked in export."""
        from caps.overrides import filter_export_fields
        _flush_user(_USERS["no_caps"])
        data = [{"title": "Secret Title", "content": "user@example.com"}]
        result = filter_export_fields("Note", data, _USERS["no_caps"])
        self.assertEqual(result[0]["content"], "us***")

    def test_admin_no_filtering_export(self):
        """Administrator export should not be filtered."""
        from caps.overrides import filter_export_fields
        data = [{"title": "Secret", "content": "user@example.com"}]
        result = filter_export_fields("Note", data, "Administrator")
        self.assertEqual(result[0]["title"], "Secret")
        self.assertEqual(result[0]["content"], "user@example.com")

    def test_multiple_rows(self):
        """Should mask across multiple rows."""
        from caps.overrides import filter_export_fields
        _flush_user(_USERS["no_caps"])
        data = [
            {"title": "T1", "content": "abc@example.com"},
            {"title": "T2", "content": "xyz@example.com"},
        ]
        result = filter_export_fields("Note", data, _USERS["no_caps"])
        self.assertEqual(result[0]["title"], "")
        self.assertEqual(result[1]["title"], "")
        self.assertEqual(result[0]["content"], "ab***")
        self.assertEqual(result[1]["content"], "xy***")


class TestApplyMask(unittest.TestCase):
    """Tests for _apply_mask pattern engine."""

    def test_last4_pattern(self):
        from caps.overrides import _apply_mask
        result = _apply_mask("1234567890", "***{last4}")
        self.assertEqual(result, "***7890")

    def test_first2_pattern(self):
        from caps.overrides import _apply_mask
        result = _apply_mask("Hello World", "{first2}***")
        self.assertEqual(result, "He***")

    def test_combined_pattern(self):
        from caps.overrides import _apply_mask
        result = _apply_mask("1234567890", "{first2}***{last4}")
        self.assertEqual(result, "12***7890")

    def test_stars_only(self):
        from caps.overrides import _apply_mask
        result = _apply_mask("anything", "***")
        self.assertEqual(result, "***")

    def test_empty_pattern_uses_dots(self):
        from caps.overrides import _apply_mask
        result = _apply_mask("12345", "")
        self.assertEqual(result, "●●●●●")

    def test_short_value_last(self):
        """If value is shorter than lastN, return whole value."""
        from caps.overrides import _apply_mask
        result = _apply_mask("AB", "***{last4}")
        self.assertEqual(result, "***AB")

    def test_short_value_first(self):
        """If value is shorter than firstN, return whole value."""
        from caps.overrides import _apply_mask
        result = _apply_mask("A", "{first2}***")
        self.assertEqual(result, "A***")

    def test_default_mask_max_8(self):
        """Default mask (empty pattern) should cap at 8 dots."""
        from caps.overrides import _apply_mask
        result = _apply_mask("abcdefghijklmnop", "")
        self.assertEqual(result, "●●●●●●●●")
        self.assertEqual(len(result), 8)
