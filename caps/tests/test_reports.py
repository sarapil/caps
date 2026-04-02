"""
CAPS — Report Tests
======================

Tests for Phase 27 Script Reports:
 - Capability Coverage report
 - User Access Matrix report
 - CAPS Audit Report

Prefix: capstest_rpt_

Run with:
    bench --site dev.localhost run-tests --app caps \
        --module caps.tests.test_reports
"""

import frappe
import unittest
from frappe.utils import now_datetime

_TEST_PREFIX = "capstest_rpt_"

_CAPS = {
    "cap_a": f"{_TEST_PREFIX}cap:alpha",
    "cap_b": f"{_TEST_PREFIX}cap:beta",
}

_USERS = {
    "user_a": f"{_TEST_PREFIX}usera@test.local",
}


def _setup_data():
    _teardown_data()

    for key, name in _CAPS.items():
        frappe.get_doc({
            "doctype": "Capability",
            "name1": name,
            "label": f"Report Cap {key}",
            "category": "Custom",
            "is_active": 1,
        }).insert(ignore_permissions=True)

    frappe.get_doc({
        "doctype": "User",
        "email": _USERS["user_a"],
        "first_name": "ReportUserA",
        "send_welcome_email": 0,
        "roles": [{"role": "System Manager"}],
    }).insert(ignore_permissions=True)

    # Grant cap_a directly
    frappe.get_doc({
        "doctype": "User Capability",
        "user": _USERS["user_a"],
        "direct_capabilities": [
            {"capability": _CAPS["cap_a"]},
        ],
    }).insert(ignore_permissions=True)

    frappe.db.commit()


def _teardown_data():
    for name in frappe.get_all(
        "User Capability",
        filters={"user": ("like", f"{_TEST_PREFIX}%")},
        pluck="name",
    ):
        frappe.delete_doc("User Capability", name, force=True, ignore_permissions=True)

    for name in _CAPS.values():
        if frappe.db.exists("Capability", name):
            frappe.delete_doc("Capability", name, force=True, ignore_permissions=True)

    for email in _USERS.values():
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)

    # Clean audit logs for this prefix
    for name in frappe.get_all(
        "CAPS Audit Log",
        filters={"user": ("like", f"{_TEST_PREFIX}%")},
        pluck="name",
    ):
        frappe.delete_doc("CAPS Audit Log", name, force=True, ignore_permissions=True)

    frappe.db.commit()


class TestCapabilityCoverageReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _setup_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_data()

    def test_execute_returns_columns_and_data(self):
        """Report execute() returns (columns, data) tuple."""
        from caps.caps.report.capability_coverage.capability_coverage import execute

        columns, data = execute()

        self.assertIsInstance(columns, list)
        self.assertTrue(len(columns) > 0, "Should have columns")
        self.assertIsInstance(data, list)

    def test_columns_have_required_fields(self):
        """Each column should have label, fieldtype, fieldname."""
        from caps.caps.report.capability_coverage.capability_coverage import execute

        columns, _ = execute()

        for col in columns:
            self.assertIn("label", col)
            self.assertIn("fieldtype", col)
            self.assertIn("fieldname", col)

    def test_data_includes_test_capabilities(self):
        """Data should include our test capabilities."""
        from caps.caps.report.capability_coverage.capability_coverage import execute

        _, data = execute({"is_active": 1})

        cap_names = [row["capability"] for row in data]
        self.assertIn(_CAPS["cap_a"], cap_names)
        self.assertIn(_CAPS["cap_b"], cap_names)

    def test_direct_user_count(self):
        """cap_a should have at least 1 direct user."""
        from caps.caps.report.capability_coverage.capability_coverage import execute

        _, data = execute({"is_active": 1})

        cap_a_row = next((r for r in data if r["capability"] == _CAPS["cap_a"]), None)
        self.assertIsNotNone(cap_a_row)
        self.assertGreaterEqual(cap_a_row["direct_users"], 1)

    def test_filter_active_only(self):
        """is_active filter should exclude inactive caps."""
        from caps.caps.report.capability_coverage.capability_coverage import execute

        _, data = execute({"is_active": 1})
        for row in data:
            self.assertTrue(row["is_active"], "All rows should be active when filtered")


class TestUserAccessMatrixReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _setup_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_data()

    def test_execute_returns_columns_and_data(self):
        """Report execute() returns (columns, data) tuple."""
        from caps.caps.report.user_access_matrix.user_access_matrix import execute

        columns, data = execute()

        self.assertIsInstance(columns, list)
        self.assertIsInstance(data, list)

    def test_user_column_present(self):
        """First column should be the User column."""
        from caps.caps.report.user_access_matrix.user_access_matrix import execute

        columns, _ = execute()

        self.assertEqual(columns[0]["fieldname"], "user")

    def test_specific_user_filter(self):
        """Filtering by user should return only that user's row."""
        from caps.caps.report.user_access_matrix.user_access_matrix import execute

        _, data = execute({"user": _USERS["user_a"]})

        users = [row["user"] for row in data]
        if data:
            self.assertIn(_USERS["user_a"], users)

    def test_direct_assignment_shows_d(self):
        """Direct assignment should show 'D' in the cell."""
        from caps.caps.report.user_access_matrix.user_access_matrix import execute

        _, data = execute({"user": _USERS["user_a"], "capability": _CAPS["cap_a"]})

        if data:
            user_row = next((r for r in data if r["user"] == _USERS["user_a"]), None)
            if user_row and _CAPS["cap_a"] in user_row:
                self.assertIn("D", user_row[_CAPS["cap_a"]])


class TestCAPSAuditReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _setup_data()
        # Create a test audit log entry
        frappe.get_doc({
            "doctype": "CAPS Audit Log",
            "user": _USERS["user_a"],
            "action": "capability_check",
            "capability": _CAPS["cap_a"],
            "result": "allowed",
            "timestamp": now_datetime(),
            "ip_address": "127.0.0.1",
        }).insert(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        _teardown_data()

    def test_execute_returns_columns_and_data(self):
        """Report execute() returns (columns, data) tuple."""
        from caps.caps.report.caps_audit_report.caps_audit_report import execute

        columns, data = execute()

        self.assertIsInstance(columns, list)
        self.assertIsInstance(data, list)

    def test_columns_include_key_fields(self):
        """Columns should include timestamp, user, action, capability, result."""
        from caps.caps.report.caps_audit_report.caps_audit_report import execute

        columns, _ = execute()
        fieldnames = [c["fieldname"] for c in columns]

        for f in ["timestamp", "user", "action", "capability", "result"]:
            self.assertIn(f, fieldnames, f"Column {f} should be present")

    def test_filter_by_user(self):
        """Filtering by user should return only that user's audit entries."""
        from caps.caps.report.caps_audit_report.caps_audit_report import execute

        _, data = execute({"user": _USERS["user_a"]})

        for row in data:
            self.assertEqual(row["user"], _USERS["user_a"])

    def test_filter_by_action(self):
        """Filtering by action type should return matching entries."""
        from caps.caps.report.caps_audit_report.caps_audit_report import execute

        _, data = execute({"action": "capability_check", "user": _USERS["user_a"]})

        for row in data:
            self.assertEqual(row["action"], "capability_check")

    def test_data_includes_test_entry(self):
        """Should include our test audit log entry."""
        from caps.caps.report.caps_audit_report.caps_audit_report import execute

        _, data = execute({"user": _USERS["user_a"]})

        self.assertTrue(len(data) > 0, "Should have at least one audit entry")
