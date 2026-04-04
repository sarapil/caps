# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS — Performance Optimization Tests (Phase 32)
==================================================

Tests for lazy resolution, differential cache, batch resolution, cache warming.

Prefix: capstest_perf_

Run with:
    bench --site dev.localhost run-tests --app caps \
        --module caps.tests.test_performance
"""

import frappe
import unittest

_PREFIX = "capstest_perf_"

_CAPS = {
    "alpha": f"{_PREFIX}cap:alpha",
    "beta": f"{_PREFIX}cap:beta",
    "gamma": f"{_PREFIX}cap:gamma",
}

_USERS = {
    "alice": f"{_PREFIX}alice@test.local",
    "bob": f"{_PREFIX}bob@test.local",
}


def _setup_data():
    _teardown_data()

    # Create capabilities
    for key, name in _CAPS.items():
        frappe.get_doc({
            "doctype": "Capability",
            "name1": name,
            "label": f"Perf {key}",
            "category": "Custom",
            "is_active": 1,
        }).insert(ignore_permissions=True)

    # Create users
    for key, email in _USERS.items():
        frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": key.title(),
            "send_welcome_email": 0,
            "roles": [{"role": "System Manager"}],
        }).insert(ignore_permissions=True)

    # Direct grants: alice=alpha+beta, bob=gamma
    frappe.get_doc({
        "doctype": "User Capability",
        "user": _USERS["alice"],
        "direct_capabilities": [
            {"capability": _CAPS["alpha"]},
            {"capability": _CAPS["beta"]},
        ],
    }).insert(ignore_permissions=True)

    frappe.get_doc({
        "doctype": "User Capability",
        "user": _USERS["bob"],
        "direct_capabilities": [
            {"capability": _CAPS["gamma"]},
        ],
    }).insert(ignore_permissions=True)

    frappe.db.commit()


def _teardown_data():
    # User Capabilities
    for email in _USERS.values():
        for uc in frappe.get_all("User Capability", filters={"user": email}, pluck="name"):
            frappe.delete_doc("User Capability", uc, force=True, ignore_permissions=True)

    # Capabilities
    for name in _CAPS.values():
        if frappe.db.exists("Capability", name):
            frappe.delete_doc("Capability", name, force=True, ignore_permissions=True)

    # Users
    for email in _USERS.values():
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)

    # Clear caches
    for email in _USERS.values():
        frappe.cache.delete_value(f"caps:user:{email}")
        for name in _CAPS.values():
            frappe.cache.delete_value(f"caps:single:{email}:{name}")

    frappe.db.commit()


class TestLazyResolution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _setup_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_data()

    def setUp(self):
        # Clear caches before each test
        for email in _USERS.values():
            frappe.cache.delete_value(f"caps:user:{email}")
            for name in _CAPS.values():
                frappe.cache.delete_value(f"caps:single:{email}:{name}")

    def test_lazy_has_direct(self):
        """lazy_has_capability should find directly assigned capabilities."""
        from caps.performance import lazy_has_capability
        self.assertTrue(lazy_has_capability(_CAPS["alpha"], _USERS["alice"]))
        self.assertFalse(lazy_has_capability(_CAPS["gamma"], _USERS["alice"]))

    def test_lazy_caches_result(self):
        """Second call should use single-cap cache."""
        from caps.performance import lazy_has_capability

        lazy_has_capability(_CAPS["alpha"], _USERS["alice"])

        # Check cache is set
        key = f"caps:single:{_USERS['alice']}:{_CAPS['alpha']}"
        cached = frappe.cache.get_value(key)
        self.assertIsNotNone(cached)

    def test_lazy_with_full_cache(self):
        """Should use full resolved cache if available."""
        from caps.performance import lazy_has_capability
        from caps.utils.resolver import resolve_capabilities

        # Pre-populate full cache
        caps_set = resolve_capabilities(_USERS["alice"])

        result = lazy_has_capability(_CAPS["alpha"], _USERS["alice"])
        self.assertTrue(result)


class TestDifferentialCache(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _setup_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_data()

    def test_apply_delta_add(self):
        """Should add capabilities to cached set."""
        from caps.performance import apply_cache_delta
        from caps.utils.resolver import resolve_capabilities

        # Pre-populate cache
        resolve_capabilities(_USERS["bob"])

        apply_cache_delta(_USERS["bob"], added=[_CAPS["alpha"]], removed=[])

        # Check cache now contains added cap
        cached = frappe.cache.get_value(f"caps:user:{_USERS['bob']}")
        self.assertIsNotNone(cached)
        self.assertIn(_CAPS["alpha"], cached)

    def test_apply_delta_remove(self):
        """Should remove capabilities from cached set."""
        from caps.performance import apply_cache_delta
        from caps.utils.resolver import resolve_capabilities

        # Pre-populate cache
        resolve_capabilities(_USERS["bob"])

        apply_cache_delta(_USERS["bob"], added=[], removed=[_CAPS["gamma"]])

        cached = frappe.cache.get_value(f"caps:user:{_USERS['bob']}")
        self.assertIsNotNone(cached)
        self.assertNotIn(_CAPS["gamma"], cached)

    def test_apply_delta_no_cache(self):
        """Should do nothing if no cache exists."""
        from caps.performance import apply_cache_delta

        frappe.cache.delete_value(f"caps:user:{_USERS['bob']}")

        # Should not raise
        apply_cache_delta(_USERS["bob"], added=[_CAPS["alpha"]], removed=[])


class TestBatchResolve(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _setup_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_data()

    def setUp(self):
        for email in _USERS.values():
            frappe.cache.delete_value(f"caps:user:{email}")

    def test_batch_resolve_both_users(self):
        """batch_resolve should return caps for multiple users."""
        from caps.performance import batch_resolve

        results = batch_resolve(list(_USERS.values()))

        self.assertIn(_USERS["alice"], results)
        self.assertIn(_USERS["bob"], results)

        self.assertIn(_CAPS["alpha"], results[_USERS["alice"]])
        self.assertIn(_CAPS["beta"], results[_USERS["alice"]])
        self.assertIn(_CAPS["gamma"], results[_USERS["bob"]])

    def test_batch_resolve_caches(self):
        """batch_resolve should cache results."""
        from caps.performance import batch_resolve

        batch_resolve(list(_USERS.values()))

        cached = frappe.cache.get_value(f"caps:user:{_USERS['alice']}")
        self.assertIsNotNone(cached)


class TestCacheWarming(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _setup_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_data()

    def setUp(self):
        for email in _USERS.values():
            frappe.cache.delete_value(f"caps:user:{email}")

    def test_warm_caches_runs(self):
        """warm_caches should run without error."""
        from caps.performance import warm_caches
        warm_caches(max_users=5)
        # Should not raise

    def test_warm_map_caches_runs(self):
        """warm_map_caches should run without error."""
        from caps.performance import warm_map_caches
        warm_map_caches()
        # Should not raise
