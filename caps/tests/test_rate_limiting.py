"""
CAPS — Rate Limiting Tests (Phase 29)
=======================================

Tests for the rate limiter engine and Capability Rate Limit DocType.

Prefix: capstest_ratelimit_

Run with:
    bench --site dev.localhost run-tests --app caps \
        --module caps.tests.test_rate_limiting
"""

import frappe
import unittest

_PREFIX = "capstest_ratelimit_"

_CAPS = {
    "limited": f"{_PREFIX}cap:limited",
    "unlimited": f"{_PREFIX}cap:unlimited",
}

_USER = f"{_PREFIX}user@test.local"


def _setup_data():
    _teardown_data()

    # Create capabilities
    for key, name in _CAPS.items():
        frappe.get_doc({
            "doctype": "Capability",
            "name1": name,
            "label": f"RateLimit {key}",
            "category": "Custom",
            "is_active": 1,
        }).insert(ignore_permissions=True)

    # Create user
    frappe.get_doc({
        "doctype": "User",
        "email": _USER,
        "first_name": "RateLimitTest",
        "send_welcome_email": 0,
        "roles": [{"role": "System Manager"}],
    }).insert(ignore_permissions=True)

    # Create rate limit rule
    frappe.get_doc({
        "doctype": "Capability Rate Limit",
        "capability": _CAPS["limited"],
        "is_active": 1,
        "max_per_hour": 3,
        "max_per_day": 10,
        "max_per_week": 0,
        "max_per_month": 0,
        "scope": "Per User",
        "notify_on_limit": 1,
    }).insert(ignore_permissions=True)

    frappe.db.commit()

    # Clear rate rule cache
    frappe.cache.delete_value("caps:rate_rules")


def _teardown_data():
    # Clean rate limits
    for name in _CAPS.values():
        for rl in frappe.get_all(
            "Capability Rate Limit",
            filters={"capability": name},
            pluck="name",
        ):
            frappe.delete_doc("Capability Rate Limit", rl, force=True, ignore_permissions=True)

    # Clean capabilities
    for name in _CAPS.values():
        if frappe.db.exists("Capability", name):
            frappe.delete_doc("Capability", name, force=True, ignore_permissions=True)

    # Clean user
    if frappe.db.exists("User", _USER):
        frappe.delete_doc("User", _USER, force=True, ignore_permissions=True)

    frappe.cache.delete_value("caps:rate_rules")
    frappe.db.commit()


class TestRateLimitDocType(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _setup_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_data()

    def test_rate_limit_exists(self):
        """Rate limit rule should be created."""
        rules = frappe.get_all(
            "Capability Rate Limit",
            filters={"capability": _CAPS["limited"]},
        )
        self.assertEqual(len(rules), 1)

    def test_validation_negative_limit(self):
        """Negative limits should be rejected."""
        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc({
                "doctype": "Capability Rate Limit",
                "capability": _CAPS["unlimited"],
                "is_active": 1,
                "max_per_hour": -1,
                "max_per_day": 0,
            }).insert(ignore_permissions=True)

    def test_validation_all_zeros(self):
        """All-zero limits should be rejected."""
        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc({
                "doctype": "Capability Rate Limit",
                "capability": _CAPS["unlimited"],
                "is_active": 1,
                "max_per_hour": 0,
                "max_per_day": 0,
                "max_per_week": 0,
                "max_per_month": 0,
            }).insert(ignore_permissions=True)


class TestRateLimiterEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _setup_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_data()

    def setUp(self):
        # Reset counters before each test
        from caps.rate_limiter import reset_usage
        reset_usage(_CAPS["limited"], _USER)

    def test_check_within_limit(self):
        """Check should pass when under limit."""
        from caps.rate_limiter import check_rate_limit
        result = check_rate_limit(_CAPS["limited"], _USER)
        self.assertTrue(result["allowed"])

    def test_check_no_rule_always_allowed(self):
        """Capabilities without rules should always be allowed."""
        from caps.rate_limiter import check_rate_limit
        result = check_rate_limit(_CAPS["unlimited"], _USER)
        self.assertTrue(result["allowed"])

    def test_record_and_check(self):
        """Recording usage should decrement remaining count."""
        from caps.rate_limiter import check_rate_limit, record_usage, get_usage_stats

        record_usage(_CAPS["limited"], _USER)
        stats = get_usage_stats(_CAPS["limited"], _USER)

        self.assertIn("hour", stats)
        self.assertEqual(stats["hour"]["used"], 1)
        self.assertEqual(stats["hour"]["remaining"], 2)

    def test_exceed_hourly_limit(self):
        """Should be blocked after exceeding hourly limit."""
        from caps.rate_limiter import check_rate_limit, record_usage

        for _ in range(3):
            record_usage(_CAPS["limited"], _USER)

        result = check_rate_limit(_CAPS["limited"], _USER)
        self.assertFalse(result["allowed"])
        self.assertIn("Rate limit exceeded", result["message"])

    def test_reset_usage(self):
        """reset_usage should clear counters."""
        from caps.rate_limiter import record_usage, get_usage_stats, reset_usage

        record_usage(_CAPS["limited"], _USER)
        record_usage(_CAPS["limited"], _USER)

        reset_usage(_CAPS["limited"], _USER)
        stats = get_usage_stats(_CAPS["limited"], _USER)

        if "hour" in stats:
            self.assertEqual(stats["hour"]["used"], 0)

    def test_limits_info_in_response(self):
        """Check response should contain limits info."""
        from caps.rate_limiter import check_rate_limit, record_usage

        record_usage(_CAPS["limited"], _USER)
        result = check_rate_limit(_CAPS["limited"], _USER)

        self.assertIn("limits", result)
        self.assertIn("hour", result["limits"])
        self.assertEqual(result["limits"]["hour"]["limit"], 3)
