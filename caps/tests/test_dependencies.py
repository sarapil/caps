"""
CAPS — Phase 8 Tests: Capability Dependencies
================================================

Tests for prerequisite child DocType, circular dependency detection,
resolver prerequisite enforcement, grant prereq checking, and
dependency graph API.

Run with:
    bench --site dev.localhost run-tests --app caps \
        --module caps.tests.test_dependencies
"""

import frappe
import unittest

_P = "capstest_dep_"

_CAPS = {
    "base":   f"{_P}cap:base",
    "mid":    f"{_P}cap:mid",
    "top":    f"{_P}cap:top",
    "island": f"{_P}cap:island",
    "soft":   f"{_P}cap:soft_dep",
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

    # mid requires base (hard)
    doc = frappe.get_doc("Capability", _CAPS["mid"])
    doc.append("prerequisites", {"prerequisite": _CAPS["base"], "is_hard": 1})
    doc.save(ignore_permissions=True)

    # top requires mid (hard) → transitive: top needs mid needs base
    doc = frappe.get_doc("Capability", _CAPS["top"])
    doc.append("prerequisites", {"prerequisite": _CAPS["mid"], "is_hard": 1})
    doc.save(ignore_permissions=True)

    # soft_dep requires base (soft — not hard)
    doc = frappe.get_doc("Capability", _CAPS["soft"])
    doc.append("prerequisites", {"prerequisite": _CAPS["base"], "is_hard": 0})
    doc.save(ignore_permissions=True)

    for key, email in _USERS.items():
        if not frappe.db.exists("User", email):
            frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": "CAPSDep",
                "last_name": key,
                "send_welcome_email": 0,
                "user_type": "System User",
            }).insert(ignore_permissions=True)

    frappe.db.commit()


def _teardown():
    frappe.cache.delete_value("caps:prereq_map")

    for email in _USERS.values():
        if frappe.db.exists("User Capability", email):
            frappe.delete_doc("User Capability", email, force=True)

    # Clear prereqs from caps before deleting
    for name in _CAPS.values():
        if frappe.db.exists("Capability", name):
            doc = frappe.get_doc("Capability", name)
            doc.prerequisites = []
            doc.save(ignore_permissions=True)

    for name in _CAPS.values():
        if frappe.db.exists("Capability", name):
            frappe.delete_doc("Capability", name, force=True)

    for email in _USERS.values():
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True)

    frappe.db.commit()


class TestPrerequisiteValidation(unittest.TestCase):
    """Test Capability controller prerequisite validations."""

    @classmethod
    def setUpClass(cls):
        _setup()

    @classmethod
    def tearDownClass(cls):
        _teardown()

    def test_self_reference_rejected(self):
        """Cannot add self as prerequisite."""
        doc = frappe.get_doc("Capability", _CAPS["island"])
        doc.append("prerequisites", {"prerequisite": _CAPS["island"], "is_hard": 1})
        with self.assertRaises(frappe.ValidationError):
            doc.save()
        doc.reload()

    def test_duplicate_prerequisite_rejected(self):
        """Cannot add same prerequisite twice."""
        doc = frappe.get_doc("Capability", _CAPS["island"])
        doc.append("prerequisites", {"prerequisite": _CAPS["base"], "is_hard": 1})
        doc.append("prerequisites", {"prerequisite": _CAPS["base"], "is_hard": 1})
        with self.assertRaises(frappe.ValidationError):
            doc.save()
        doc.reload()

    def test_circular_dependency_rejected(self):
        """Circular dependency: base → top → mid → base should be rejected."""
        doc = frappe.get_doc("Capability", _CAPS["base"])
        doc.append("prerequisites", {"prerequisite": _CAPS["top"], "is_hard": 1})
        with self.assertRaises(frappe.ValidationError):
            doc.save()
        doc.reload()

    def test_valid_prerequisite_accepted(self):
        """Valid prerequisite can be added."""
        doc = frappe.get_doc("Capability", _CAPS["island"])
        doc.prerequisites = []
        doc.append("prerequisites", {"prerequisite": _CAPS["base"], "is_hard": 1})
        doc.save(ignore_permissions=True)
        self.assertEqual(len(doc.prerequisites), 1)
        # Cleanup
        doc.prerequisites = []
        doc.save(ignore_permissions=True)


class TestResolverPrereqEnforcement(unittest.TestCase):
    """Test that the resolver enforces hard prerequisites."""

    @classmethod
    def setUpClass(cls):
        _setup()

    @classmethod
    def tearDownClass(cls):
        _teardown()

    def setUp(self):
        frappe.cache.delete_value("caps:prereq_map")
        from caps.utils.resolver import invalidate_all_caches
        invalidate_all_caches()

    def _grant(self, user, caps):
        if not frappe.db.exists("User Capability", user):
            frappe.get_doc({"doctype": "User Capability", "user": user}).insert(ignore_permissions=True)
        doc = frappe.get_doc("User Capability", user)
        doc.direct_capabilities = []
        for c in caps:
            doc.append("direct_capabilities", {"capability": c})
        doc.save(ignore_permissions=True)
        from caps.utils.resolver import invalidate_user_cache
        invalidate_user_cache(user)

    def test_cap_with_prereq_met(self):
        """mid is kept when base is present."""
        self._grant(_USERS["u1"], [_CAPS["base"], _CAPS["mid"]])
        from caps.utils.resolver import resolve_capabilities
        caps = resolve_capabilities(_USERS["u1"])
        self.assertIn(_CAPS["mid"], caps)
        self.assertIn(_CAPS["base"], caps)

    def test_cap_without_prereq_removed(self):
        """mid is removed when base is missing (hard prereq)."""
        self._grant(_USERS["u1"], [_CAPS["mid"]])
        from caps.utils.resolver import resolve_capabilities
        caps = resolve_capabilities(_USERS["u1"])
        self.assertNotIn(_CAPS["mid"], caps)

    def test_transitive_prereq_enforcement(self):
        """top needs mid needs base — giving only top+mid drops both."""
        self._grant(_USERS["u1"], [_CAPS["top"], _CAPS["mid"]])
        from caps.utils.resolver import resolve_capabilities
        caps = resolve_capabilities(_USERS["u1"])
        # mid is removed (no base), then top is removed (no mid)
        self.assertNotIn(_CAPS["top"], caps)
        self.assertNotIn(_CAPS["mid"], caps)

    def test_transitive_prereq_all_met(self):
        """top+mid+base all present → all kept."""
        self._grant(_USERS["u1"], [_CAPS["base"], _CAPS["mid"], _CAPS["top"]])
        from caps.utils.resolver import resolve_capabilities
        caps = resolve_capabilities(_USERS["u1"])
        self.assertIn(_CAPS["top"], caps)
        self.assertIn(_CAPS["mid"], caps)
        self.assertIn(_CAPS["base"], caps)

    def test_soft_prereq_not_enforced(self):
        """soft_dep has a soft prereq on base — kept even without base."""
        self._grant(_USERS["u1"], [_CAPS["soft"]])
        from caps.utils.resolver import resolve_capabilities
        caps = resolve_capabilities(_USERS["u1"])
        self.assertIn(_CAPS["soft"], caps)

    def test_no_prereqs_unaffected(self):
        """island has no prereqs — always kept."""
        self._grant(_USERS["u1"], [_CAPS["island"]])
        from caps.utils.resolver import resolve_capabilities
        caps = resolve_capabilities(_USERS["u1"])
        self.assertIn(_CAPS["island"], caps)


class TestDependencyGraphAPI(unittest.TestCase):
    """Test the dependency graph API endpoints."""

    @classmethod
    def setUpClass(cls):
        _setup()

    @classmethod
    def tearDownClass(cls):
        _teardown()

    def test_single_capability_graph(self):
        """Get dep graph for 'top' → should show top→mid→base."""
        from caps.utils.resolver import get_dependency_graph
        graph = get_dependency_graph(_CAPS["top"])
        self.assertIn("nodes", graph)
        self.assertIn("edges", graph)
        node_names = {n["name"] for n in graph["nodes"]}
        self.assertIn(_CAPS["top"], node_names)
        self.assertIn(_CAPS["mid"], node_names)
        self.assertIn(_CAPS["base"], node_names)
        # Edges: top→mid and mid→base
        edge_pairs = {(e["from"], e["to"]) for e in graph["edges"]}
        self.assertIn((_CAPS["top"], _CAPS["mid"]), edge_pairs)
        self.assertIn((_CAPS["mid"], _CAPS["base"]), edge_pairs)

    def test_full_graph(self):
        """Full dep graph includes all edges."""
        from caps.utils.resolver import get_dependency_graph
        graph = get_dependency_graph()
        edge_pairs = {(e["from"], e["to"]) for e in graph["edges"]}
        self.assertIn((_CAPS["top"], _CAPS["mid"]), edge_pairs)
        self.assertIn((_CAPS["mid"], _CAPS["base"]), edge_pairs)
        # soft dep edge too
        self.assertIn((_CAPS["soft"], _CAPS["base"]), edge_pairs)

    def test_island_no_deps(self):
        """island capability has no dependencies."""
        from caps.utils.resolver import get_dependency_graph
        graph = get_dependency_graph(_CAPS["island"])
        self.assertEqual(len(graph["edges"]), 0)
        self.assertEqual(len(graph["nodes"]), 1)
        self.assertEqual(graph["nodes"][0]["name"], _CAPS["island"])

    def test_api_check_prerequisites(self):
        """check_prerequisites API works correctly."""
        # Grant only 'mid' (missing its prereq 'base')
        if not frappe.db.exists("User Capability", _USERS["u1"]):
            frappe.get_doc({"doctype": "User Capability", "user": _USERS["u1"]}).insert(ignore_permissions=True)
        doc = frappe.get_doc("User Capability", _USERS["u1"])
        doc.direct_capabilities = []
        doc.append("direct_capabilities", {"capability": _CAPS["mid"]})
        doc.save(ignore_permissions=True)
        frappe.cache.delete_value(f"caps:user:{_USERS['u1']}")

        from caps.api import check_prerequisites
        result = check_prerequisites(_CAPS["mid"], _USERS["u1"])
        self.assertFalse(result["met"])
        self.assertIn(_CAPS["base"], result["missing"])


class TestGrantPrereqCheck(unittest.TestCase):
    """Test that grant_capability checks prerequisites."""

    @classmethod
    def setUpClass(cls):
        _setup()

    @classmethod
    def tearDownClass(cls):
        _teardown()

    def setUp(self):
        frappe.cache.delete_value("caps:prereq_map")
        from caps.utils.resolver import invalidate_all_caches
        invalidate_all_caches()
        # Clean user caps
        if frappe.db.exists("User Capability", _USERS["u1"]):
            frappe.delete_doc("User Capability", _USERS["u1"], force=True)
        frappe.db.commit()

    def test_grant_with_missing_prereq_fails(self):
        """Granting 'mid' without 'base' should fail."""
        from caps.api import grant_capability
        with self.assertRaises(frappe.ValidationError):
            grant_capability(_USERS["u1"], _CAPS["mid"])

    def test_grant_with_prereq_met_succeeds(self):
        """Granting 'mid' with 'base' already present should succeed."""
        from caps.api import grant_capability
        # First grant base (no prereqs)
        grant_capability(_USERS["u1"], _CAPS["base"])
        frappe.cache.delete_value(f"caps:user:{_USERS['u1']}")
        # Now grant mid (prereq base is met)
        grant_capability(_USERS["u1"], _CAPS["mid"])
        doc = frappe.get_doc("User Capability", _USERS["u1"])
        cap_names = [r.capability for r in doc.direct_capabilities]
        self.assertIn(_CAPS["mid"], cap_names)
