# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS — Group Hierarchy Tests
================================

Tests for Permission Group hierarchy (Phase 26):
 - Ancestor traversal in resolver._collect_from_groups
 - Temporary membership (valid_from / valid_till filtering)
 - Cache invalidation cascade to child groups
 - Group hierarchy API endpoints
 - _expand_group_ancestors / _get_group_hierarchy_map

Prefix: capstest_grphier_

Run with:
    bench --site dev.localhost run-tests --app caps \
        --module caps.tests.test_group_hierarchy
"""

import frappe
import unittest
from frappe.utils import now_datetime, add_days, add_to_date

_TEST_PREFIX = "capstest_grphier_"

_CAPS = {
    "root_cap": f"{_TEST_PREFIX}cap:root",
    "parent_cap": f"{_TEST_PREFIX}cap:parent",
    "child_cap": f"{_TEST_PREFIX}cap:child",
}

_GROUPS = {
    "root": f"{_TEST_PREFIX}root_group",
    "parent": f"{_TEST_PREFIX}parent_group",
    "child": f"{_TEST_PREFIX}child_group",
}

_USERS = {
    "root_member": f"{_TEST_PREFIX}rootmember@test.local",
    "child_member": f"{_TEST_PREFIX}childmember@test.local",
    "temp_member": f"{_TEST_PREFIX}tempmember@test.local",
}


def _setup_data():
    _teardown_data()

    # Create capabilities
    for key, name in _CAPS.items():
        frappe.get_doc({
            "doctype": "Capability",
            "name1": name,
            "label": f"GrpHier {key}",
            "category": "Custom",
            "is_active": 1,
        }).insert(ignore_permissions=True)

    # Create users
    for key, email in _USERS.items():
        frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": f"GrpHier{key.title()}",
            "send_welcome_email": 0,
            "roles": [{"role": "System Manager"}],
        }).insert(ignore_permissions=True)

    # Create group hierarchy: root → parent → child
    frappe.get_doc({
        "doctype": "Permission Group",
        "__newname": _GROUPS["root"],
        "label": "Root Group",
        "group_type": "Manual",
        "group_capabilities": [
            {"capability": _CAPS["root_cap"]},
        ],
        "members": [
            {
                "user": _USERS["root_member"],
                "added_by": "Administrator",
                "added_on": now_datetime(),
            },
        ],
    }).insert(ignore_permissions=True)

    frappe.get_doc({
        "doctype": "Permission Group",
        "__newname": _GROUPS["parent"],
        "label": "Parent Group",
        "group_type": "Manual",
        "parent_group": _GROUPS["root"],
        "group_capabilities": [
            {"capability": _CAPS["parent_cap"]},
        ],
    }).insert(ignore_permissions=True)

    frappe.get_doc({
        "doctype": "Permission Group",
        "__newname": _GROUPS["child"],
        "label": "Child Group",
        "group_type": "Manual",
        "parent_group": _GROUPS["parent"],
        "group_capabilities": [
            {"capability": _CAPS["child_cap"]},
        ],
        "members": [
            {
                "user": _USERS["child_member"],
                "added_by": "Administrator",
                "added_on": now_datetime(),
            },
        ],
    }).insert(ignore_permissions=True)

    # Create User Capability docs so resolver finds users
    for email in _USERS.values():
        if not frappe.db.exists("User Capability", email):
            frappe.get_doc({
                "doctype": "User Capability",
                "user": email,
            }).insert(ignore_permissions=True)

    # Ensure group hierarchy setting is enabled
    frappe.db.set_single_value("CAPS Settings", "enable_group_hierarchy", 1)
    frappe.clear_cache(doctype="CAPS Settings")
    if hasattr(frappe.local, "_caps_settings"):
        del frappe.local._caps_settings

    frappe.db.commit()
    _flush()


def _teardown_data():
    # Clean user capabilities
    for email in _USERS.values():
        if frappe.db.exists("User Capability", email):
            frappe.delete_doc("User Capability", email, force=True, ignore_permissions=True)

    # Clean groups (child first to avoid FK issues)
    for key in ["child", "parent", "root"]:
        name = _GROUPS[key]
        if frappe.db.exists("Permission Group", name):
            frappe.delete_doc("Permission Group", name, force=True, ignore_permissions=True)

    # Clean capabilities
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
    frappe.cache.delete_value("caps:group_hierarchy_map")
    if hasattr(frappe.local, "_caps_settings"):
        del frappe.local._caps_settings


class TestGroupAncestorTraversal(unittest.TestCase):
    """Test that _expand_group_ancestors finds ancestor groups."""

    @classmethod
    def setUpClass(cls):
        _setup_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_data()

    def test_expand_ancestors_from_child(self):
        """Child group should expand to include parent and root."""
        from caps.utils.resolver import _expand_group_ancestors
        _flush()

        expanded = _expand_group_ancestors([_GROUPS["child"]])
        self.assertIn(_GROUPS["child"], expanded)
        self.assertIn(_GROUPS["parent"], expanded)
        self.assertIn(_GROUPS["root"], expanded)

    def test_expand_ancestors_from_parent(self):
        """Parent group should expand to include root but not child."""
        from caps.utils.resolver import _expand_group_ancestors
        _flush()

        expanded = _expand_group_ancestors([_GROUPS["parent"]])
        self.assertIn(_GROUPS["parent"], expanded)
        self.assertIn(_GROUPS["root"], expanded)
        self.assertNotIn(_GROUPS["child"], expanded)

    def test_expand_ancestors_root_stays_same(self):
        """Root group has no parent — expanded list is just root."""
        from caps.utils.resolver import _expand_group_ancestors
        _flush()

        expanded = _expand_group_ancestors([_GROUPS["root"]])
        self.assertEqual(sorted(expanded), sorted([_GROUPS["root"]]))

    def test_hierarchy_map_cached(self):
        """_get_group_hierarchy_map returns correct parent mapping."""
        from caps.utils.resolver import _get_group_hierarchy_map
        _flush()

        hmap = _get_group_hierarchy_map()
        self.assertEqual(hmap.get(_GROUPS["child"]), _GROUPS["parent"])
        self.assertEqual(hmap.get(_GROUPS["parent"]), _GROUPS["root"])
        self.assertIsNone(hmap.get(_GROUPS["root"]))


class TestGroupHierarchyResolution(unittest.TestCase):
    """Test that child group members inherit ancestor group capabilities."""

    @classmethod
    def setUpClass(cls):
        _setup_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_data()

    def test_child_member_gets_all_ancestor_caps(self):
        """User in child group should resolve child + parent + root caps."""
        from caps.utils.resolver import resolve_capabilities
        _flush()

        caps = resolve_capabilities(_USERS["child_member"])
        self.assertIn(_CAPS["child_cap"], caps, "Should have child group cap")
        self.assertIn(_CAPS["parent_cap"], caps, "Should inherit parent group cap")
        self.assertIn(_CAPS["root_cap"], caps, "Should inherit root group cap")

    def test_root_member_only_gets_root_caps(self):
        """User in root group should only get root caps, not child/parent."""
        from caps.utils.resolver import resolve_capabilities
        _flush()

        caps = resolve_capabilities(_USERS["root_member"])
        self.assertIn(_CAPS["root_cap"], caps, "Should have root group cap")
        self.assertNotIn(_CAPS["child_cap"], caps, "Should NOT get child group cap")
        self.assertNotIn(_CAPS["parent_cap"], caps, "Should NOT get parent group cap")

    def test_hierarchy_disabled_no_inheritance(self):
        """When enable_group_hierarchy is disabled, no ancestor inheritance."""
        from caps.utils.resolver import resolve_capabilities

        frappe.db.set_single_value("CAPS Settings", "enable_group_hierarchy", 0)
        frappe.db.commit()
        frappe.clear_cache(doctype="CAPS Settings")
        if hasattr(frappe.local, "_caps_settings"):
            del frappe.local._caps_settings
        _flush()

        try:
            caps = resolve_capabilities(_USERS["child_member"])
            self.assertIn(_CAPS["child_cap"], caps, "Should still have direct group cap")
            self.assertNotIn(_CAPS["root_cap"], caps, "Should NOT inherit when disabled")
        finally:
            frappe.db.set_single_value("CAPS Settings", "enable_group_hierarchy", 1)
            frappe.db.commit()
            frappe.clear_cache(doctype="CAPS Settings")
            if hasattr(frappe.local, "_caps_settings"):
                del frappe.local._caps_settings
            _flush()


class TestTempMembership(unittest.TestCase):
    """Test valid_from / valid_till temporary membership filtering."""

    @classmethod
    def setUpClass(cls):
        _setup_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_data()

    def test_expired_membership_excluded(self):
        """A member with valid_till in the past should not get group caps."""
        from caps.utils.resolver import resolve_capabilities

        # Add temp_member to child group with expired valid_till
        doc = frappe.get_doc("Permission Group", _GROUPS["child"])
        doc.append("members", {
            "user": _USERS["temp_member"],
            "added_by": "Administrator",
            "added_on": now_datetime(),
            "valid_till": add_days(now_datetime(), -1),  # yesterday
        })
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        _flush()

        try:
            caps = resolve_capabilities(_USERS["temp_member"])
            self.assertNotIn(_CAPS["child_cap"], caps,
                             "Expired temp membership should not grant caps")
        finally:
            # Remove temp member
            doc.reload()
            doc.members = [m for m in doc.members if m.user != _USERS["temp_member"]]
            doc.save(ignore_permissions=True)
            frappe.db.commit()
            _flush()

    def test_future_membership_excluded(self):
        """A member with valid_from in the future should not get group caps yet."""
        from caps.utils.resolver import resolve_capabilities

        doc = frappe.get_doc("Permission Group", _GROUPS["child"])
        doc.append("members", {
            "user": _USERS["temp_member"],
            "added_by": "Administrator",
            "added_on": now_datetime(),
            "valid_from": add_days(now_datetime(), 7),  # next week
        })
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        _flush()

        try:
            caps = resolve_capabilities(_USERS["temp_member"])
            self.assertNotIn(_CAPS["child_cap"], caps,
                             "Future membership should not grant caps yet")
        finally:
            doc.reload()
            doc.members = [m for m in doc.members if m.user != _USERS["temp_member"]]
            doc.save(ignore_permissions=True)
            frappe.db.commit()
            _flush()

    def test_active_temp_membership_included(self):
        """A member with valid_from in the past and valid_till in the future should work."""
        from caps.utils.resolver import resolve_capabilities

        doc = frappe.get_doc("Permission Group", _GROUPS["child"])
        doc.append("members", {
            "user": _USERS["temp_member"],
            "added_by": "Administrator",
            "added_on": now_datetime(),
            "valid_from": add_days(now_datetime(), -1),  # yesterday
            "valid_till": add_days(now_datetime(), 7),   # next week
        })
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        _flush()

        try:
            caps = resolve_capabilities(_USERS["temp_member"])
            self.assertIn(_CAPS["child_cap"], caps,
                          "Active temp membership should grant caps")
        finally:
            doc.reload()
            doc.members = [m for m in doc.members if m.user != _USERS["temp_member"]]
            doc.save(ignore_permissions=True)
            frappe.db.commit()
            _flush()


class TestGroupCacheInvalidation(unittest.TestCase):
    """Test cache invalidation cascades for group hierarchy."""

    @classmethod
    def setUpClass(cls):
        _setup_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_data()

    def test_parent_change_invalidates_child_members(self):
        """Changing root group should also invalidate child member caches."""
        from caps.utils.resolver import resolve_capabilities

        # Warm cache for child_member
        resolve_capabilities(_USERS["child_member"])

        # Modify root group (this should cascade invalidation)
        doc = frappe.get_doc("Permission Group", _GROUPS["root"])
        doc.save(ignore_permissions=True)
        frappe.db.commit()

        # The cache for child_member should be cleared
        cache_key = f"caps:user:{_USERS['child_member']}"
        cached = frappe.cache.get_value(cache_key)
        self.assertIsNone(cached, "Child member cache should be invalidated on parent change")

    def test_hierarchy_map_cleared_on_group_change(self):
        """Group hierarchy map cache should be cleared when a group changes."""
        from caps.utils.resolver import _get_group_hierarchy_map

        # Warm the cache
        _get_group_hierarchy_map()
        self.assertIsNotNone(frappe.cache.get_value("caps:group_hierarchy_map"))

        # Save a group
        doc = frappe.get_doc("Permission Group", _GROUPS["parent"])
        doc.save(ignore_permissions=True)
        frappe.db.commit()

        # Cache should be cleared
        cached = frappe.cache.get_value("caps:group_hierarchy_map")
        self.assertIsNone(cached, "Group hierarchy cache should be cleared")


class TestGroupAPI(unittest.TestCase):
    """Test Group Hierarchy API endpoints."""

    @classmethod
    def setUpClass(cls):
        _setup_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_data()

    def test_get_group_tree(self):
        """get_group_tree returns nested tree structure."""
        from caps.api_groups import get_group_tree

        frappe.set_user("Administrator")
        tree = get_group_tree()

        # Find our root group in the tree
        root_node = None
        for node in tree:
            if node["name"] == _GROUPS["root"]:
                root_node = node
                break

        self.assertIsNotNone(root_node, "Root group should be in tree")
        # Root should have parent as child
        child_names = [c["name"] for c in root_node.get("children", [])]
        self.assertIn(_GROUPS["parent"], child_names, "Parent should be child of root")

    def test_get_group_ancestors(self):
        """get_group_ancestors returns parent chain."""
        from caps.api_groups import get_group_ancestors

        frappe.set_user("Administrator")
        ancestors = get_group_ancestors(_GROUPS["child"])

        self.assertEqual(len(ancestors), 2)
        self.assertEqual(ancestors[0], _GROUPS["parent"])
        self.assertEqual(ancestors[1], _GROUPS["root"])

    def test_get_group_descendants(self):
        """get_group_descendants returns child chain."""
        from caps.api_groups import get_group_descendants

        frappe.set_user("Administrator")
        descendants = get_group_descendants(_GROUPS["root"])

        self.assertIn(_GROUPS["parent"], descendants)
        self.assertIn(_GROUPS["child"], descendants)

    def test_get_effective_members(self):
        """get_effective_members returns group members."""
        from caps.api_groups import get_effective_members

        frappe.set_user("Administrator")
        members = get_effective_members(_GROUPS["child"])

        user_emails = [m["user"] for m in members]
        self.assertIn(_USERS["child_member"], user_emails)

    def test_get_effective_capabilities(self):
        """get_effective_capabilities returns caps from group."""
        from caps.api_groups import get_effective_capabilities

        frappe.set_user("Administrator")
        caps = get_effective_capabilities(_GROUPS["child"], include_ancestors=True)

        cap_names = [c["capability"] for c in caps]
        self.assertIn(_CAPS["child_cap"], cap_names)
        self.assertIn(_CAPS["parent_cap"], cap_names)
        self.assertIn(_CAPS["root_cap"], cap_names)

    def test_get_effective_capabilities_direct_only(self):
        """Without include_ancestors, only direct caps returned."""
        from caps.api_groups import get_effective_capabilities

        frappe.set_user("Administrator")
        caps = get_effective_capabilities(_GROUPS["child"], include_ancestors=False)

        cap_names = [c["capability"] for c in caps]
        self.assertIn(_CAPS["child_cap"], cap_names)
        self.assertNotIn(_CAPS["root_cap"], cap_names)

    def test_add_temp_member(self):
        """add_temp_member adds a user with temporal bounds."""
        from caps.api_groups import add_temp_member

        frappe.set_user("Administrator")

        result = add_temp_member(
            group=_GROUPS["root"],
            user=_USERS["temp_member"],
            valid_from=str(add_days(now_datetime(), -1)),
            valid_till=str(add_days(now_datetime(), 30)),
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["member"]["user"], _USERS["temp_member"])

        # Verify in DB
        doc = frappe.get_doc("Permission Group", _GROUPS["root"])
        temp_members = [m for m in doc.members if m.user == _USERS["temp_member"]]
        self.assertEqual(len(temp_members), 1)
        self.assertIsNotNone(temp_members[0].valid_from)
        self.assertIsNotNone(temp_members[0].valid_till)

        # Clean up
        doc.members = [m for m in doc.members if m.user != _USERS["temp_member"]]
        doc.save(ignore_permissions=True)
        frappe.db.commit()
