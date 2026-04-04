# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS — Cache Invalidation Tests
==================================

Tests for caps.cache_invalidation handlers that are triggered via
doc_events in hooks.py.

Run with:
    bench --site dev.localhost run-tests --app caps \
        --module caps.tests.test_cache_invalidation
"""

import frappe
import unittest

_TEST_PREFIX = "capstest_ci_"

_CAP_NAMES = [
    f"{_TEST_PREFIX}cap:x",
    f"{_TEST_PREFIX}cap:y",
    f"{_TEST_PREFIX}cap:z",
]

_BUNDLE_NAME = f"{_TEST_PREFIX}bundle"
_GROUP_NAME = f"{_TEST_PREFIX}group"
_ROLE_NAME = f"{_TEST_PREFIX}role"

_USERS = {
    "u1": f"{_TEST_PREFIX}u1@test.local",
    "u2": f"{_TEST_PREFIX}u2@test.local",
}


def _setup_ci_data():
    _teardown_ci_data()

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
        "capabilities": [
            {"capability": f"{_TEST_PREFIX}cap:x"},
        ],
    }).insert(ignore_permissions=True)

    # Role
    if not frappe.db.exists("Role", _ROLE_NAME):
        frappe.get_doc({
            "doctype": "Role",
            "role_name": _ROLE_NAME,
            "desk_access": 1,
        }).insert(ignore_permissions=True)

    # Users
    for key, email in _USERS.items():
        if not frappe.db.exists("User", email):
            roles = [{"role": _ROLE_NAME}] if key == "u1" else []
            frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": "CAPSCI",
                "last_name": key,
                "send_welcome_email": 0,
                "user_type": "System User",
                "roles": roles,
            }).insert(ignore_permissions=True)

    # User Capability for u1
    frappe.get_doc({
        "doctype": "User Capability",
        "user": _USERS["u1"],
        "direct_capabilities": [
            {"capability": f"{_TEST_PREFIX}cap:x"},
        ],
    }).insert(ignore_permissions=True)

    # Permission Group with u2
    frappe.get_doc({
        "doctype": "Permission Group",
        "__newname": _GROUP_NAME,
        "label": _GROUP_NAME,
        "group_type": "Manual",
        "members": [{"user": _USERS["u2"]}],
        "group_capabilities": [{"capability": f"{_TEST_PREFIX}cap:y"}],
    }).insert(ignore_permissions=True)

    # Role Capability Map
    frappe.get_doc({
        "doctype": "Role Capability Map",
        "role": _ROLE_NAME,
        "role_capabilities": [{"capability": f"{_TEST_PREFIX}cap:z"}],
    }).insert(ignore_permissions=True)

    frappe.db.commit()


def _teardown_ci_data():
    for email in _USERS.values():
        frappe.cache.delete_value(f"caps:user:{email}")

    if frappe.db.exists("Role Capability Map", _ROLE_NAME):
        frappe.delete_doc("Role Capability Map", _ROLE_NAME,
                          force=True, ignore_permissions=True)

    for name in frappe.get_all("Permission Group",
                               filters={"label": _GROUP_NAME}, pluck="name"):
        frappe.delete_doc("Permission Group", name,
                          force=True, ignore_permissions=True)

    for email in _USERS.values():
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

    if frappe.db.exists("Role", _ROLE_NAME):
        frappe.delete_doc("Role", _ROLE_NAME,
                          force=True, ignore_permissions=True)

    frappe.db.commit()


def _populate_cache(user):
    """Resolve and cache capabilities for a user."""
    frappe.cache.delete_value(f"caps:user:{user}")
    from caps.utils.resolver import resolve_capabilities
    resolve_capabilities(user)


def _cache_exists(user):
    return frappe.cache.get_value(f"caps:user:{user}") is not None


# ── Tests ─────────────────────────────────────────────────────────────


class TestUserCapabilityChange(unittest.TestCase):
    """on_user_capability_change → invalidate that user's cache."""

    @classmethod
    def setUpClass(cls):
        _setup_ci_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_ci_data()

    def test_update_invalidates_cache(self):
        user = _USERS["u1"]
        _populate_cache(user)
        self.assertTrue(_cache_exists(user))

        # Trigger via doc event (update the UserCapability)
        doc = frappe.get_doc("User Capability", user)
        doc.append("direct_capabilities", {
            "capability": f"{_TEST_PREFIX}cap:y",
        })
        doc.save(ignore_permissions=True)
        frappe.db.commit()

        # Cache should be invalidated by on_user_capability_change
        self.assertFalse(_cache_exists(user))

        # Cleanup — remove the added cap
        doc.reload()
        for row in doc.direct_capabilities:
            if row.capability == f"{_TEST_PREFIX}cap:y":
                doc.remove(row)
                break
        doc.save(ignore_permissions=True)
        frappe.db.commit()


class TestPermissionGroupChange(unittest.TestCase):
    """on_permission_group_change → invalidate all group members' caches."""

    @classmethod
    def setUpClass(cls):
        _setup_ci_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_ci_data()

    def test_group_update_invalidates_member_cache(self):
        user = _USERS["u2"]
        _populate_cache(user)
        self.assertTrue(_cache_exists(user))

        # Update the group — add a capability
        grp = frappe.get_doc("Permission Group", _GROUP_NAME)
        grp.append("group_capabilities", {
            "capability": f"{_TEST_PREFIX}cap:z",
        })
        grp.save(ignore_permissions=True)
        frappe.db.commit()

        # u2's cache should be invalidated
        self.assertFalse(_cache_exists(user))

        # Cleanup
        grp.reload()
        for row in grp.group_capabilities:
            if row.capability == f"{_TEST_PREFIX}cap:z":
                grp.remove(row)
                break
        grp.save(ignore_permissions=True)
        frappe.db.commit()


class TestBundleChange(unittest.TestCase):
    """on_bundle_change → invalidate users referencing the bundle."""

    @classmethod
    def setUpClass(cls):
        _setup_ci_data()
        # Assign bundle directly to u1
        doc = frappe.get_doc("User Capability", _USERS["u1"])
        doc.append("direct_bundles", {"bundle": _BUNDLE_NAME})
        doc.save(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        _teardown_ci_data()

    def test_bundle_update_invalidates_user_cache(self):
        user = _USERS["u1"]
        _populate_cache(user)
        self.assertTrue(_cache_exists(user))

        # Update the bundle — add a capability
        bundle = frappe.get_doc("Capability Bundle", _BUNDLE_NAME)
        bundle.append("capabilities", {
            "capability": f"{_TEST_PREFIX}cap:y",
        })
        bundle.save(ignore_permissions=True)
        frappe.db.commit()

        # u1's cache should be invalidated
        self.assertFalse(_cache_exists(user))

        # Cleanup
        bundle.reload()
        for row in bundle.capabilities:
            if row.capability == f"{_TEST_PREFIX}cap:y":
                bundle.remove(row)
                break
        bundle.save(ignore_permissions=True)
        frappe.db.commit()


class TestRoleMapChange(unittest.TestCase):
    """on_role_map_change → invalidate all users with that role."""

    @classmethod
    def setUpClass(cls):
        _setup_ci_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_ci_data()

    def test_role_map_update_invalidates_user_cache(self):
        user = _USERS["u1"]  # has the role
        _populate_cache(user)
        self.assertTrue(_cache_exists(user))

        # Update the role capability map
        rcm = frappe.get_doc("Role Capability Map", _ROLE_NAME)
        rcm.append("role_capabilities", {
            "capability": f"{_TEST_PREFIX}cap:y",
        })
        rcm.save(ignore_permissions=True)
        frappe.db.commit()

        self.assertFalse(_cache_exists(user))

        # Cleanup
        rcm.reload()
        for row in rcm.role_capabilities:
            if row.capability == f"{_TEST_PREFIX}cap:y":
                rcm.remove(row)
                break
        rcm.save(ignore_permissions=True)
        frappe.db.commit()


class TestFieldActionMapChange(unittest.TestCase):
    """on_field_map_change / on_action_map_change → bump version."""

    @classmethod
    def setUpClass(cls):
        _setup_ci_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_ci_data()

    def test_field_map_change_bumps_version(self):
        old_version = int(frappe.cache.get_value("caps:map_version") or 0)

        doc = frappe.get_doc({
            "doctype": "Field Capability Map",
            "doctype_name": "Note",
            "fieldname": "title",
            "capability": f"{_TEST_PREFIX}cap:x",
            "behavior": "hide",
            "priority": 1,
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        new_version = int(frappe.cache.get_value("caps:map_version") or 0)
        self.assertGreater(new_version, old_version)

        # Cleanup
        doc.delete(force=True, ignore_permissions=True)
        frappe.db.commit()

    def test_action_map_change_bumps_version(self):
        old_version = int(frappe.cache.get_value("caps:map_version") or 0)

        doc = frappe.get_doc({
            "doctype": "Action Capability Map",
            "doctype_name": "Note",
            "action_id": f"{_TEST_PREFIX}test_action",
            "action_type": "button",
            "capability": f"{_TEST_PREFIX}cap:x",
            "fallback_behavior": "hide",
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        new_version = int(frappe.cache.get_value("caps:map_version") or 0)
        self.assertGreater(new_version, old_version)

        # Cleanup
        doc.delete(force=True, ignore_permissions=True)
        frappe.db.commit()
