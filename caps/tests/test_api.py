"""
CAPS — API Endpoint Tests
============================

Tests for all 10 whitelisted endpoints in caps.api.

Run with:
    bench --site dev.localhost run-tests --app caps \
        --module caps.tests.test_api
"""

import json
import frappe
import unittest
from frappe.utils import now_datetime, add_days

_TEST_PREFIX = "capstest_api_"

_CAP_NAMES = [
    f"{_TEST_PREFIX}cap:alpha",
    f"{_TEST_PREFIX}cap:beta",
    f"{_TEST_PREFIX}cap:gamma",
]

_USERS = {
    "user1": f"{_TEST_PREFIX}user1@test.local",
    "user2": f"{_TEST_PREFIX}user2@test.local",
}


def _setup_api_data():
    _teardown_api_data()

    for cap_name in _CAP_NAMES:
        frappe.get_doc({
            "doctype": "Capability",
            "name1": cap_name,
            "label": cap_name,
            "category": "Custom",
            "is_active": 1,
        }).insert(ignore_permissions=True)

    for key, email in _USERS.items():
        if not frappe.db.exists("User", email):
            frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": "CAPSApi",
                "last_name": key,
                "send_welcome_email": 0,
                "user_type": "System User",
            }).insert(ignore_permissions=True)

    # Grant alpha+beta to user1, gamma to user2
    frappe.get_doc({
        "doctype": "User Capability",
        "user": _USERS["user1"],
        "direct_capabilities": [
            {"capability": f"{_TEST_PREFIX}cap:alpha"},
            {"capability": f"{_TEST_PREFIX}cap:beta"},
        ],
    }).insert(ignore_permissions=True)

    frappe.get_doc({
        "doctype": "User Capability",
        "user": _USERS["user2"],
        "direct_capabilities": [
            {"capability": f"{_TEST_PREFIX}cap:gamma"},
        ],
    }).insert(ignore_permissions=True)

    frappe.db.commit()


def _teardown_api_data():
    for email in _USERS.values():
        frappe.cache.delete_value(f"caps:user:{email}")
        if frappe.db.exists("User Capability", email):
            frappe.delete_doc("User Capability", email,
                              force=True, ignore_permissions=True)

    for cap_name in _CAP_NAMES:
        if frappe.db.exists("Capability", cap_name):
            frappe.delete_doc("Capability", cap_name,
                              force=True, ignore_permissions=True)

    for email in _USERS.values():
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email,
                              force=True, ignore_permissions=True)

    frappe.db.commit()


def _flush(user):
    frappe.cache.delete_value(f"caps:user:{user}")


# ── Tests ─────────────────────────────────────────────────────────────


class TestCheckCapability(unittest.TestCase):
    """Tests for caps.api.check_capability."""

    @classmethod
    def setUpClass(cls):
        _setup_api_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_api_data()

    def test_check_true(self):
        from caps.api import check_capability
        _flush(_USERS["user1"])
        old_user = frappe.session.user
        frappe.set_user(_USERS["user1"])
        try:
            result = check_capability(f"{_TEST_PREFIX}cap:alpha")
            self.assertTrue(result)
        finally:
            frappe.set_user(old_user)

    def test_check_false(self):
        from caps.api import check_capability
        _flush(_USERS["user1"])
        old_user = frappe.session.user
        frappe.set_user(_USERS["user1"])
        try:
            result = check_capability(f"{_TEST_PREFIX}cap:gamma")
            self.assertFalse(result)
        finally:
            frappe.set_user(old_user)


class TestCheckCapabilities(unittest.TestCase):
    """Tests for caps.api.check_capabilities (batch check)."""

    @classmethod
    def setUpClass(cls):
        _setup_api_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_api_data()

    def test_batch_check_list(self):
        from caps.api import check_capabilities
        _flush(_USERS["user1"])
        old_user = frappe.session.user
        frappe.set_user(_USERS["user1"])
        try:
            result = check_capabilities([
                f"{_TEST_PREFIX}cap:alpha",
                f"{_TEST_PREFIX}cap:gamma",
            ])
            self.assertTrue(result[f"{_TEST_PREFIX}cap:alpha"])
            self.assertFalse(result[f"{_TEST_PREFIX}cap:gamma"])
        finally:
            frappe.set_user(old_user)

    def test_batch_check_json_string(self):
        from caps.api import check_capabilities
        _flush(_USERS["user1"])
        old_user = frappe.session.user
        frappe.set_user(_USERS["user1"])
        try:
            caps_json = json.dumps([
                f"{_TEST_PREFIX}cap:alpha",
                f"{_TEST_PREFIX}cap:beta",
            ])
            result = check_capabilities(caps_json)
            self.assertTrue(result[f"{_TEST_PREFIX}cap:alpha"])
            self.assertTrue(result[f"{_TEST_PREFIX}cap:beta"])
        finally:
            frappe.set_user(old_user)


class TestGetMyCapabilities(unittest.TestCase):
    """Tests for caps.api.get_my_capabilities."""

    @classmethod
    def setUpClass(cls):
        _setup_api_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_api_data()

    def test_returns_sorted_list(self):
        from caps.api import get_my_capabilities
        _flush(_USERS["user1"])
        old_user = frappe.session.user
        frappe.set_user(_USERS["user1"])
        try:
            result = get_my_capabilities()
            self.assertIsInstance(result, list)
            # Should contain alpha and beta
            self.assertIn(f"{_TEST_PREFIX}cap:alpha", result)
            self.assertIn(f"{_TEST_PREFIX}cap:beta", result)
            # Should be sorted
            self.assertEqual(result, sorted(result))
        finally:
            frappe.set_user(old_user)


class TestBustCache(unittest.TestCase):
    """Tests for caps.api.bust_cache."""

    @classmethod
    def setUpClass(cls):
        _setup_api_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_api_data()

    def test_bust_cache_clears(self):
        from caps.api import bust_cache
        from caps.utils.resolver import resolve_capabilities

        user = _USERS["user1"]
        _flush(user)
        resolve_capabilities(user)  # populate cache
        cached = frappe.cache.get_value(f"caps:user:{user}")
        self.assertIsNotNone(cached)

        old_user = frappe.session.user
        frappe.set_user(user)
        try:
            result = bust_cache()
            self.assertEqual(result["status"], "ok")
        finally:
            frappe.set_user(old_user)

        cached = frappe.cache.get_value(f"caps:user:{user}")
        self.assertIsNone(cached)


class TestAdminGetUserCapabilities(unittest.TestCase):
    """Tests for caps.api.get_user_capabilities (admin-only)."""

    @classmethod
    def setUpClass(cls):
        _setup_api_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_api_data()

    def test_returns_breakdown(self):
        from caps.api import get_user_capabilities
        _flush(_USERS["user1"])
        old_user = frappe.session.user
        frappe.set_user("Administrator")
        try:
            result = get_user_capabilities(_USERS["user1"])
            self.assertEqual(result["user"], _USERS["user1"])
            self.assertGreaterEqual(result["total_count"], 2)
            self.assertIn(f"{_TEST_PREFIX}cap:alpha", result["direct"])
            self.assertIn(f"{_TEST_PREFIX}cap:beta", result["direct"])
            self.assertIn(f"{_TEST_PREFIX}cap:alpha", result["all"])
        finally:
            frappe.set_user(old_user)

    def test_non_admin_blocked(self):
        from caps.api import get_user_capabilities
        old_user = frappe.session.user
        frappe.set_user(_USERS["user1"])
        try:
            with self.assertRaises(frappe.PermissionError):
                get_user_capabilities(_USERS["user2"])
        finally:
            frappe.set_user(old_user)


class TestAdminCompareUsers(unittest.TestCase):
    """Tests for caps.api.compare_users (admin-only)."""

    @classmethod
    def setUpClass(cls):
        _setup_api_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_api_data()

    def test_compare_returns_diff(self):
        from caps.api import compare_users
        for u in _USERS.values():
            _flush(u)
        old_user = frappe.session.user
        frappe.set_user("Administrator")
        try:
            result = compare_users(_USERS["user1"], _USERS["user2"])
            self.assertIn(f"{_TEST_PREFIX}cap:alpha", result["only_user1"])
            self.assertIn(f"{_TEST_PREFIX}cap:gamma", result["only_user2"])
            # No shared test-prefix caps
            shared_test = [c for c in result["shared"] if c.startswith(_TEST_PREFIX)]
            self.assertEqual(shared_test, [])
        finally:
            frappe.set_user(old_user)


class TestAdminGrantRevoke(unittest.TestCase):
    """Tests for caps.api.grant_capability and revoke_capability."""

    @classmethod
    def setUpClass(cls):
        _setup_api_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_api_data()

    def test_grant_new_capability(self):
        from caps.api import grant_capability
        from caps.utils.resolver import has_capability
        user = _USERS["user2"]
        _flush(user)

        old_user = frappe.session.user
        frappe.set_user("Administrator")
        try:
            result = grant_capability(user, f"{_TEST_PREFIX}cap:alpha")
            self.assertEqual(result["status"], "granted")
        finally:
            frappe.set_user(old_user)

        _flush(user)
        self.assertTrue(has_capability(f"{_TEST_PREFIX}cap:alpha", user))

        # Cleanup — revoke it
        frappe.set_user("Administrator")
        try:
            from caps.api import revoke_capability
            revoke_capability(user, f"{_TEST_PREFIX}cap:alpha")
        finally:
            frappe.set_user(old_user)

    def test_grant_duplicate_throws(self):
        from caps.api import grant_capability
        user = _USERS["user1"]
        _flush(user)
        old_user = frappe.session.user
        frappe.set_user("Administrator")
        try:
            with self.assertRaises(Exception):
                grant_capability(user, f"{_TEST_PREFIX}cap:alpha")
        finally:
            frappe.set_user(old_user)

    def test_revoke_existing(self):
        from caps.api import grant_capability, revoke_capability
        from caps.utils.resolver import has_capability
        user = _USERS["user2"]
        _flush(user)
        old_user = frappe.session.user
        frappe.set_user("Administrator")
        try:
            grant_capability(user, f"{_TEST_PREFIX}cap:beta")
            _flush(user)
            self.assertTrue(has_capability(f"{_TEST_PREFIX}cap:beta", user))

            result = revoke_capability(user, f"{_TEST_PREFIX}cap:beta")
            self.assertEqual(result["status"], "revoked")
        finally:
            frappe.set_user(old_user)

        _flush(user)
        self.assertFalse(has_capability(f"{_TEST_PREFIX}cap:beta", user))

    def test_revoke_nonexistent_throws(self):
        from caps.api import revoke_capability
        user = _USERS["user2"]
        old_user = frappe.session.user
        frappe.set_user("Administrator")
        try:
            with self.assertRaises(Exception):
                revoke_capability(user, f"{_TEST_PREFIX}cap:alpha")
        finally:
            frappe.set_user(old_user)

    def test_grant_creates_audit_log(self):
        from caps.api import grant_capability, revoke_capability
        user = _USERS["user2"]
        _flush(user)
        old_user = frappe.session.user
        frappe.set_user("Administrator")
        try:
            grant_capability(user, f"{_TEST_PREFIX}cap:alpha")
            frappe.db.commit()

            logs = frappe.get_all("CAPS Audit Log", filters={
                "target_user": user,
                "capability": f"{_TEST_PREFIX}cap:alpha",
                "action": "capability_granted",
            })
            self.assertGreater(len(logs), 0)

            # Cleanup
            revoke_capability(user, f"{_TEST_PREFIX}cap:alpha")
        finally:
            frappe.set_user(old_user)
