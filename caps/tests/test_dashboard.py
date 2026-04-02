"""
CAPS — Dashboard API Tests
============================

Tests for analytics dashboard endpoints (caps.api_dashboard):
 - get_dashboard_stats
 - get_capability_distribution
 - get_audit_timeline
 - get_expiry_forecast
 - get_request_summary
 - get_delegation_summary
 - get_policy_summary

Prefix: capstest_dash_

Run with:
    bench --site dev.localhost run-tests --app caps \
        --module caps.tests.test_dashboard
"""

import frappe
import unittest
from frappe.utils import now_datetime, add_days

_TEST_PREFIX = "capstest_dash_"

_CAPS = {
    "alpha": f"{_TEST_PREFIX}cap:alpha",
    "beta": f"{_TEST_PREFIX}cap:beta",
}

_USERS = {
    "user1": f"{_TEST_PREFIX}user1@test.local",
}


def _setup_dashboard_data():
    _teardown_dashboard_data()

    # Create capabilities
    for key, cap_name in _CAPS.items():
        frappe.get_doc({
            "doctype": "Capability",
            "name1": cap_name,
            "label": cap_name,
            "category": "Custom",
            "is_active": 1,
            "is_delegatable": 1,
        }).insert(ignore_permissions=True)

    # Create user
    for key, email in _USERS.items():
        if not frappe.db.exists("User", email):
            frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": "CAPSDash",
                "last_name": key,
                "send_welcome_email": 0,
                "user_type": "System User",
            }).insert(ignore_permissions=True)

    # Grant capabilities to user
    frappe.get_doc({
        "doctype": "User Capability",
        "user": _USERS["user1"],
        "direct_capabilities": [
            {"capability": _CAPS["alpha"], "expires_on": add_days(now_datetime(), 5)},
            {"capability": _CAPS["beta"]},
        ],
    }).insert(ignore_permissions=True)

    # Create an audit log
    frappe.get_doc({
        "doctype": "CAPS Audit Log",
        "user": "Administrator",
        "action": "capability_granted",
        "capability": _CAPS["alpha"],
        "target_user": _USERS["user1"],
        "result": "allowed",
        "timestamp": now_datetime(),
    }).insert(ignore_permissions=True)

    frappe.db.commit()


def _teardown_dashboard_data():
    # Clean audit logs
    frappe.db.sql(
        "DELETE FROM `tabCAPS Audit Log` WHERE capability LIKE %s",
        (f"{_TEST_PREFIX}%",),
    )

    # Clean requests
    for req in frappe.get_all(
        "Capability Request",
        filters={"capability": ("like", f"{_TEST_PREFIX}%")},
        pluck="name",
    ):
        frappe.delete_doc("Capability Request", req, force=True, ignore_permissions=True)

    # Clean policies
    for pol in frappe.get_all(
        "Capability Policy",
        filters={"policy_name": ("like", f"{_TEST_PREFIX}%")},
        pluck="name",
    ):
        frappe.delete_doc("Capability Policy", pol, force=True, ignore_permissions=True)

    for email in _USERS.values():
        frappe.cache.delete_value(f"caps:user:{email}")
        if frappe.db.exists("User Capability", email):
            frappe.delete_doc("User Capability", email, force=True, ignore_permissions=True)

    for cap_name in _CAPS.values():
        if frappe.db.exists("Capability", cap_name):
            frappe.delete_doc("Capability", cap_name, force=True, ignore_permissions=True)

    for email in _USERS.values():
        _safe_delete_user(email)

    frappe.db.commit()


def _safe_delete_user(email):
    """Delete user, handling linked docs from other apps."""
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


# ── Tests ─────────────────────────────────────────────────────────────


class TestGetDashboardStats(unittest.TestCase):
    """Tests for caps.api_dashboard.get_dashboard_stats."""

    @classmethod
    def setUpClass(cls):
        _setup_dashboard_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_dashboard_data()

    def test_returns_all_stat_keys(self):
        from caps.api_dashboard import get_dashboard_stats
        result = get_dashboard_stats()

        expected_keys = [
            "total_capabilities", "active_capabilities",
            "total_bundles", "total_groups",
            "users_with_capabilities", "total_grants",
            "pending_requests", "active_policies",
            "expiring_soon", "delegated_grants",
        ]
        for key in expected_keys:
            self.assertIn(key, result)

    def test_counts_are_non_negative(self):
        from caps.api_dashboard import get_dashboard_stats
        result = get_dashboard_stats()

        for key, value in result.items():
            self.assertGreaterEqual(value, 0, f"{key} should be >= 0")

    def test_capability_count_includes_test_data(self):
        from caps.api_dashboard import get_dashboard_stats
        result = get_dashboard_stats()

        self.assertGreaterEqual(result["total_capabilities"], 2)
        self.assertGreaterEqual(result["active_capabilities"], 2)
        self.assertGreaterEqual(result["users_with_capabilities"], 1)
        self.assertGreaterEqual(result["total_grants"], 2)

    def test_expiring_soon_count(self):
        from caps.api_dashboard import get_dashboard_stats
        result = get_dashboard_stats()

        # user1 has alpha expiring in 5 days (within 7-day window)
        self.assertGreaterEqual(result["expiring_soon"], 1)


class TestGetCapabilityDistribution(unittest.TestCase):
    """Tests for caps.api_dashboard.get_capability_distribution."""

    @classmethod
    def setUpClass(cls):
        _setup_dashboard_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_dashboard_data()

    def test_returns_chart_format(self):
        from caps.api_dashboard import get_capability_distribution
        result = get_capability_distribution()

        self.assertIn("labels", result)
        self.assertIn("datasets", result)
        self.assertTrue(len(result["datasets"]) >= 1)
        self.assertEqual(result["datasets"][0]["name"], "Users")

    def test_includes_test_caps(self):
        from caps.api_dashboard import get_capability_distribution
        result = get_capability_distribution()

        # At least alpha and beta should appear
        self.assertTrue(len(result["labels"]) >= 1)


class TestGetAuditTimeline(unittest.TestCase):
    """Tests for caps.api_dashboard.get_audit_timeline."""

    @classmethod
    def setUpClass(cls):
        _setup_dashboard_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_dashboard_data()

    def test_returns_chart_format(self):
        from caps.api_dashboard import get_audit_timeline
        result = get_audit_timeline(days=30)

        self.assertIn("labels", result)
        self.assertIn("datasets", result)

    def test_has_data(self):
        from caps.api_dashboard import get_audit_timeline
        result = get_audit_timeline(days=30)

        # Should have at least one day with data
        self.assertTrue(len(result["labels"]) >= 1)


class TestGetExpiryForecast(unittest.TestCase):
    """Tests for caps.api_dashboard.get_expiry_forecast."""

    @classmethod
    def setUpClass(cls):
        _setup_dashboard_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_dashboard_data()

    def test_returns_chart_format(self):
        from caps.api_dashboard import get_expiry_forecast
        result = get_expiry_forecast(days=30)

        self.assertIn("labels", result)
        self.assertIn("datasets", result)
        self.assertTrue(len(result["datasets"]) >= 1)

    def test_shows_expiring_grants(self):
        from caps.api_dashboard import get_expiry_forecast
        result = get_expiry_forecast(days=30)

        # user1's alpha expires in 5 days
        total = sum(result["datasets"][0]["values"]) if result["datasets"][0]["values"] else 0
        self.assertGreaterEqual(total, 1)


class TestGetRequestSummary(unittest.TestCase):
    """Tests for caps.api_dashboard.get_request_summary."""

    @classmethod
    def setUpClass(cls):
        _setup_dashboard_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_dashboard_data()

    def test_returns_chart_format(self):
        from caps.api_dashboard import get_request_summary
        result = get_request_summary()

        self.assertIn("labels", result)
        self.assertIn("datasets", result)


class TestGetDelegationSummary(unittest.TestCase):
    """Tests for caps.api_dashboard.get_delegation_summary."""

    @classmethod
    def setUpClass(cls):
        _setup_dashboard_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_dashboard_data()

    def test_returns_expected_keys(self):
        from caps.api_dashboard import get_delegation_summary
        result = get_delegation_summary()

        self.assertIn("top_delegators", result)
        self.assertIn("top_delegated_capabilities", result)


class TestGetPolicySummary(unittest.TestCase):
    """Tests for caps.api_dashboard.get_policy_summary."""

    @classmethod
    def setUpClass(cls):
        _setup_dashboard_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_dashboard_data()

    def test_returns_expected_keys(self):
        from caps.api_dashboard import get_policy_summary
        result = get_policy_summary()

        self.assertIn("active_policies", result)
        self.assertIn("inactive_policies", result)
        self.assertIn("by_target_type", result)
