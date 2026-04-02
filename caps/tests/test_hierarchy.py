"""
CAPS — Capability Hierarchy Tests
====================================

Tests for parent→child capability inheritance:
 - _get_hierarchy_map / _expand_hierarchy (resolver)
 - get_capability_tree API endpoint
 - Cache invalidation for hierarchy

Prefix: capstest_hier_

Run with:
    bench --site dev.localhost run-tests --app caps \
        --module caps.tests.test_hierarchy
"""

import frappe
import unittest

_TEST_PREFIX = "capstest_hier_"

_CAPS = {
    "parent": f"{_TEST_PREFIX}parent:all",
    "child_a": f"{_TEST_PREFIX}child:a",
    "child_b": f"{_TEST_PREFIX}child:b",
    "grandchild": f"{_TEST_PREFIX}grandchild:x",
    "inactive_child": f"{_TEST_PREFIX}child:inactive",
    "orphan": f"{_TEST_PREFIX}orphan:standalone",
}

_USERS = {
    "holder": f"{_TEST_PREFIX}holder@test.local",
}


def _setup_hierarchy_data():
    _teardown_hierarchy_data()

    # Create capabilities
    frappe.get_doc({
        "doctype": "Capability",
        "name1": _CAPS["parent"],
        "label": "Parent All",
        "category": "Custom",
        "is_active": 1,
    }).insert(ignore_permissions=True)

    frappe.get_doc({
        "doctype": "Capability",
        "name1": _CAPS["child_a"],
        "label": "Child A",
        "category": "Custom",
        "is_active": 1,
        "parent_capability": _CAPS["parent"],
    }).insert(ignore_permissions=True)

    frappe.get_doc({
        "doctype": "Capability",
        "name1": _CAPS["child_b"],
        "label": "Child B",
        "category": "Custom",
        "is_active": 1,
        "parent_capability": _CAPS["parent"],
    }).insert(ignore_permissions=True)

    # Grandchild: child of child_a
    frappe.get_doc({
        "doctype": "Capability",
        "name1": _CAPS["grandchild"],
        "label": "Grandchild X",
        "category": "Custom",
        "is_active": 1,
        "parent_capability": _CAPS["child_a"],
    }).insert(ignore_permissions=True)

    # Inactive child: should not be inherited
    frappe.get_doc({
        "doctype": "Capability",
        "name1": _CAPS["inactive_child"],
        "label": "Inactive Child",
        "category": "Custom",
        "is_active": 0,
        "parent_capability": _CAPS["parent"],
    }).insert(ignore_permissions=True)

    # Orphan cap: no parent
    frappe.get_doc({
        "doctype": "Capability",
        "name1": _CAPS["orphan"],
        "label": "Orphan",
        "category": "Custom",
        "is_active": 1,
    }).insert(ignore_permissions=True)

    # Create user
    user = frappe.get_doc({
        "doctype": "User",
        "email": _USERS["holder"],
        "first_name": "HierHolder",
        "send_welcome_email": 0,
        "roles": [{"role": "System Manager"}],
    })
    user.insert(ignore_permissions=True)

    # Give user the parent capability and orphan via User Capability child table
    frappe.get_doc({
        "doctype": "User Capability",
        "user": _USERS["holder"],
        "direct_capabilities": [
            {"capability": _CAPS["parent"]},
            {"capability": _CAPS["orphan"]},
        ],
    }).insert(ignore_permissions=True)

    frappe.db.commit()
    _flush()


def _teardown_hierarchy_data():
    # Clean user capabilities
    for name in frappe.get_all(
        "User Capability",
        filters={"user": ("like", f"{_TEST_PREFIX}%")},
        pluck="name",
    ):
        frappe.delete_doc("User Capability", name, force=True, ignore_permissions=True)

    # Clean capabilities (grandchild first, then children, then parent)
    for cap_name in [
        _CAPS["grandchild"],
        _CAPS["child_a"],
        _CAPS["child_b"],
        _CAPS["inactive_child"],
        _CAPS["parent"],
        _CAPS["orphan"],
    ]:
        if frappe.db.exists("Capability", cap_name):
            frappe.delete_doc("Capability", cap_name, force=True, ignore_permissions=True)

    for email in _USERS.values():
        _safe_delete_user(email)

    frappe.db.commit()
    _flush()


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


def _flush():
    for email in _USERS.values():
        frappe.cache.delete_value(f"caps:user:{email}")
    frappe.cache.delete_value("caps:hierarchy_map")
    frappe.cache.delete_value("caps:prereq_map")


class TestHierarchy(unittest.TestCase):
    """Test capability hierarchy / parent→child inheritance."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        _setup_hierarchy_data()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        _teardown_hierarchy_data()

    def setUp(self):
        frappe.set_user("Administrator")
        _flush()

    # ─── _get_hierarchy_map ────────────────────────────────────────

    def test_hierarchy_map_returns_children(self):
        """_get_hierarchy_map should return {parent: [children]}."""
        from caps.utils.resolver import _get_hierarchy_map

        hmap = _get_hierarchy_map()
        # parent → child_a, child_b (inactive_child excluded because is_active=0)
        children = hmap.get(_CAPS["parent"], [])
        self.assertIn(_CAPS["child_a"], children)
        self.assertIn(_CAPS["child_b"], children)
        self.assertNotIn(_CAPS["inactive_child"], children)

    def test_hierarchy_map_multilevel(self):
        """_get_hierarchy_map should include grandchild under child_a."""
        from caps.utils.resolver import _get_hierarchy_map

        hmap = _get_hierarchy_map()
        children_of_a = hmap.get(_CAPS["child_a"], [])
        self.assertIn(_CAPS["grandchild"], children_of_a)

    def test_hierarchy_map_cached(self):
        """_get_hierarchy_map should use Redis cache on second call."""
        from caps.utils.resolver import _get_hierarchy_map

        _flush()
        h1 = _get_hierarchy_map()
        # Set a sentinel in cache
        frappe.cache.set_value("caps:hierarchy_map", {"sentinel": ["test"]})
        h2 = _get_hierarchy_map()
        self.assertEqual(h2, {"sentinel": ["test"]})

        # Clean up
        _flush()

    # ─── _expand_hierarchy ─────────────────────────────────────────

    def test_expand_hierarchy_adds_children(self):
        """User with parent cap should auto-get active children."""
        from caps.utils.resolver import _expand_hierarchy, _get_hierarchy_map

        active_caps = {
            _CAPS["parent"], _CAPS["child_a"], _CAPS["child_b"],
            _CAPS["grandchild"], _CAPS["orphan"],
        }

        user_caps = {_CAPS["parent"], _CAPS["orphan"]}
        expanded = _expand_hierarchy(user_caps, active_caps)

        self.assertIn(_CAPS["child_a"], expanded)
        self.assertIn(_CAPS["child_b"], expanded)
        self.assertIn(_CAPS["grandchild"], expanded)
        self.assertIn(_CAPS["orphan"], expanded)
        self.assertIn(_CAPS["parent"], expanded)

    def test_expand_hierarchy_skips_inactive(self):
        """Inactive children should not be inherited."""
        from caps.utils.resolver import _expand_hierarchy

        active_caps = {
            _CAPS["parent"], _CAPS["child_a"], _CAPS["child_b"],
            _CAPS["grandchild"], _CAPS["orphan"],
            # inactive_child deliberately omitted
        }

        user_caps = {_CAPS["parent"]}
        expanded = _expand_hierarchy(user_caps, active_caps)
        self.assertNotIn(_CAPS["inactive_child"], expanded)

    def test_expand_hierarchy_empty_map(self):
        """When no hierarchy exists, expand should return original set."""
        from caps.utils.resolver import _expand_hierarchy

        # Set empty hierarchy map in cache
        frappe.cache.set_value("caps:hierarchy_map", {})
        user_caps = {_CAPS["parent"]}
        expanded = _expand_hierarchy(user_caps, {_CAPS["parent"]})
        self.assertEqual(expanded, user_caps)
        _flush()

    # ─── resolve_capabilities integration ──────────────────────────

    def test_resolver_inherits_children(self):
        """resolve_capabilities should return parent + inherited children."""
        from caps.utils.resolver import resolve_capabilities

        caps = resolve_capabilities(_USERS["holder"])
        self.assertIn(_CAPS["parent"], caps)
        self.assertIn(_CAPS["child_a"], caps)
        self.assertIn(_CAPS["child_b"], caps)
        self.assertIn(_CAPS["grandchild"], caps)
        self.assertIn(_CAPS["orphan"], caps)

    def test_resolver_excludes_inactive_children(self):
        """resolve_capabilities should NOT include inactive children."""
        from caps.utils.resolver import resolve_capabilities

        caps = resolve_capabilities(_USERS["holder"])
        self.assertNotIn(_CAPS["inactive_child"], caps)

    # ─── get_capability_tree API ───────────────────────────────────

    def test_tree_full_forest(self):
        """get_capability_tree without root returns full forest."""
        from caps.api import get_capability_tree

        result = get_capability_tree()
        self.assertIn("nodes", result)
        # Root nodes should NOT have parent
        root_names = [n["name"] for n in result["nodes"]]
        # Parent and orphan should be in roots
        self.assertIn(_CAPS["parent"], root_names)
        self.assertIn(_CAPS["orphan"], root_names)
        # Children should NOT be roots
        self.assertNotIn(_CAPS["child_a"], root_names)

    def test_tree_from_root(self):
        """get_capability_tree with root returns subtree."""
        from caps.api import get_capability_tree

        result = get_capability_tree(root=_CAPS["parent"])
        self.assertEqual(len(result["nodes"]), 1)

        node = result["nodes"][0]
        self.assertEqual(node["name"], _CAPS["parent"])
        child_names = [c["name"] for c in node["children"]]
        self.assertIn(_CAPS["child_a"], child_names)
        self.assertIn(_CAPS["child_b"], child_names)

        # child_a should have grandchild
        child_a_node = next(c for c in node["children"] if c["name"] == _CAPS["child_a"])
        gc_names = [g["name"] for g in child_a_node["children"]]
        self.assertIn(_CAPS["grandchild"], gc_names)

    def test_tree_invalid_root_throws(self):
        """get_capability_tree with nonexistent root should throw."""
        from caps.api import get_capability_tree

        with self.assertRaises(Exception):
            get_capability_tree(root="nonexistent_cap_12345")

    # ─── cache invalidation ───────────────────────────────────────

    def test_hierarchy_cache_cleared_on_capability_change(self):
        """Saving a Capability should clear hierarchy cache."""
        from caps.utils.resolver import _get_hierarchy_map

        # Prime cache
        _get_hierarchy_map()

        # Confirm cache is set
        cached = frappe.cache.get_value("caps:hierarchy_map")
        self.assertIsNotNone(cached)

        # Update a capability (trigger cache invalidation)
        cap = frappe.get_doc("Capability", _CAPS["child_a"])
        cap.label = "Child A Updated"
        cap.save(ignore_permissions=True)
        frappe.db.commit()

        # Cache should be cleared
        cached_after = frappe.cache.get_value("caps:hierarchy_map")
        self.assertIsNone(cached_after)

        # Restore label
        cap.label = "Child A"
        cap.save(ignore_permissions=True)
        frappe.db.commit()
