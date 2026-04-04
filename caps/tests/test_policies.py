# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS — Temporal Policy Tests
==============================

Tests for Capability Policy DocType and policy_engine:
 - Policy validation
 - Policy active window checks
 - Target resolution (Role, Department, User List)
 - apply_policies / expire_policies
 - Preview
 - Policy grant tagging (notes field)

Prefix: capstest_pol_

Run with:
    bench --site dev.localhost run-tests --app caps \
        --module caps.tests.test_policies
"""

import frappe
import unittest
from frappe.utils import now_datetime, add_days

_TEST_PREFIX = "capstest_pol_"

_CAPS = {
    "alpha": f"{_TEST_PREFIX}cap:alpha",
    "beta": f"{_TEST_PREFIX}cap:beta",
}

_USERS = {
    "user1": f"{_TEST_PREFIX}user1@test.local",
    "user2": f"{_TEST_PREFIX}user2@test.local",
}

_ROLE = f"{_TEST_PREFIX}TestRole"


def _setup_policy_data():
    _teardown_policy_data()

    # Create capabilities
    for key, cap_name in _CAPS.items():
        frappe.get_doc({
            "doctype": "Capability",
            "name1": cap_name,
            "label": cap_name,
            "category": "Custom",
            "is_active": 1,
        }).insert(ignore_permissions=True)

    # Create test role
    if not frappe.db.exists("Role", _ROLE):
        frappe.get_doc({"doctype": "Role", "role_name": _ROLE}).insert(ignore_permissions=True)

    # Create users
    for key, email in _USERS.items():
        if not frappe.db.exists("User", email):
            u = frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": "CAPSPol",
                "last_name": key,
                "send_welcome_email": 0,
                "user_type": "System User",
            })
            u.insert(ignore_permissions=True)

    # Add test role to user1
    u1 = frappe.get_doc("User", _USERS["user1"])
    if not any(r.role == _ROLE for r in u1.roles):
        u1.append("roles", {"role": _ROLE})
        u1.save(ignore_permissions=True)

    frappe.db.commit()


def _teardown_policy_data():
    # Clean policies
    for pol in frappe.get_all(
        "Capability Policy",
        filters={"policy_name": ("like", f"{_TEST_PREFIX}%")},
        pluck="name",
    ):
        frappe.delete_doc("Capability Policy", pol, force=True, ignore_permissions=True)

    # Clean audit logs
    frappe.db.sql(
        "DELETE FROM `tabCAPS Audit Log` WHERE capability LIKE %s",
        (f"{_TEST_PREFIX}%",),
    )

    for email in _USERS.values():
        frappe.cache.delete_value(f"caps:user:{email}")
        if frappe.db.exists("User Capability", email):
            frappe.delete_doc("User Capability", email, force=True, ignore_permissions=True)

    for cap_name in _CAPS.values():
        if frappe.db.exists("Capability", cap_name):
            frappe.delete_doc("Capability", cap_name, force=True, ignore_permissions=True)

    if frappe.db.exists("Role", _ROLE):
        frappe.delete_doc("Role", _ROLE, force=True, ignore_permissions=True)

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


def _clean_policies():
    for pol in frappe.get_all(
        "Capability Policy",
        filters={"policy_name": ("like", f"{_TEST_PREFIX}%")},
        pluck="name",
    ):
        frappe.delete_doc("Capability Policy", pol, force=True, ignore_permissions=True)


def _clean_user_caps():
    for email in _USERS.values():
        frappe.cache.delete_value(f"caps:user:{email}")
        if frappe.db.exists("User Capability", email):
            frappe.delete_doc("User Capability", email, force=True, ignore_permissions=True)


# ── Tests ─────────────────────────────────────────────────────────────


class TestPolicyValidation(unittest.TestCase):
    """Tests for Capability Policy validation logic."""

    @classmethod
    def setUpClass(cls):
        _setup_policy_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_policy_data()

    def _clean(self):
        _clean_policies()

    def test_valid_policy_creation(self):
        self._clean()
        doc = frappe.get_doc({
            "doctype": "Capability Policy",
            "policy_name": f"{_TEST_PREFIX}valid_policy",
            "target_type": "Role",
            "target_role": _ROLE,
            "grant_type": "Capability",
            "capability": _CAPS["alpha"],
            "is_active": 1,
        })
        doc.insert(ignore_permissions=True)
        self.assertTrue(frappe.db.exists("Capability Policy", f"{_TEST_PREFIX}valid_policy"))

    def test_invalid_schedule_fails(self):
        self._clean()
        now = now_datetime()
        doc = frappe.get_doc({
            "doctype": "Capability Policy",
            "policy_name": f"{_TEST_PREFIX}bad_sched",
            "target_type": "Role",
            "target_role": _ROLE,
            "grant_type": "Capability",
            "capability": _CAPS["alpha"],
            "starts_on": now,
            "ends_on": add_days(now, -1),
        })
        with self.assertRaises(frappe.exceptions.ValidationError):
            doc.insert(ignore_permissions=True)

    def test_missing_role_fails(self):
        self._clean()
        doc = frappe.get_doc({
            "doctype": "Capability Policy",
            "policy_name": f"{_TEST_PREFIX}no_role",
            "target_type": "Role",
            "grant_type": "Capability",
            "capability": _CAPS["alpha"],
        })
        with self.assertRaises(frappe.exceptions.ValidationError):
            doc.insert(ignore_permissions=True)

    def test_grant_type_mismatch_fails(self):
        self._clean()
        doc = frappe.get_doc({
            "doctype": "Capability Policy",
            "policy_name": f"{_TEST_PREFIX}mismatch",
            "target_type": "Role",
            "target_role": _ROLE,
            "grant_type": "Capability",
            # Missing capability field
        })
        with self.assertRaises(frappe.exceptions.ValidationError):
            doc.insert(ignore_permissions=True)

    def test_user_list_target(self):
        self._clean()
        doc = frappe.get_doc({
            "doctype": "Capability Policy",
            "policy_name": f"{_TEST_PREFIX}user_list",
            "target_type": "User List",
            "target_users": f"{_USERS['user1']},{_USERS['user2']}",
            "grant_type": "Capability",
            "capability": _CAPS["alpha"],
            "is_active": 1,
        })
        doc.insert(ignore_permissions=True)
        self.assertTrue(frappe.db.exists("Capability Policy", f"{_TEST_PREFIX}user_list"))


class TestPolicyActiveWindow(unittest.TestCase):
    """Tests for is_currently_active()."""

    @classmethod
    def setUpClass(cls):
        _setup_policy_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_policy_data()

    def _clean(self):
        _clean_policies()

    def test_active_no_schedule(self):
        self._clean()
        doc = frappe.get_doc({
            "doctype": "Capability Policy",
            "policy_name": f"{_TEST_PREFIX}no_sched",
            "target_type": "Role",
            "target_role": _ROLE,
            "grant_type": "Capability",
            "capability": _CAPS["alpha"],
            "is_active": 1,
        })
        doc.insert(ignore_permissions=True)
        self.assertTrue(doc.is_currently_active())

    def test_inactive_flag(self):
        self._clean()
        doc = frappe.get_doc({
            "doctype": "Capability Policy",
            "policy_name": f"{_TEST_PREFIX}inactive",
            "target_type": "Role",
            "target_role": _ROLE,
            "grant_type": "Capability",
            "capability": _CAPS["alpha"],
            "is_active": 0,
        })
        doc.insert(ignore_permissions=True)
        self.assertFalse(doc.is_currently_active())

    def test_future_start(self):
        self._clean()
        doc = frappe.get_doc({
            "doctype": "Capability Policy",
            "policy_name": f"{_TEST_PREFIX}future",
            "target_type": "Role",
            "target_role": _ROLE,
            "grant_type": "Capability",
            "capability": _CAPS["alpha"],
            "is_active": 1,
            "starts_on": add_days(now_datetime(), 30),
        })
        doc.insert(ignore_permissions=True)
        self.assertFalse(doc.is_currently_active())

    def test_past_end(self):
        self._clean()
        doc = frappe.get_doc({
            "doctype": "Capability Policy",
            "policy_name": f"{_TEST_PREFIX}expired",
            "target_type": "Role",
            "target_role": _ROLE,
            "grant_type": "Capability",
            "capability": _CAPS["alpha"],
            "is_active": 1,
            "starts_on": add_days(now_datetime(), -30),
            "ends_on": add_days(now_datetime(), -1),
        })
        doc.insert(ignore_permissions=True)
        self.assertFalse(doc.is_currently_active())


class TestPolicyTargetResolution(unittest.TestCase):
    """Tests for get_target_users()."""

    @classmethod
    def setUpClass(cls):
        _setup_policy_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_policy_data()

    def _clean(self):
        _clean_policies()

    def test_role_target(self):
        self._clean()
        doc = frappe.get_doc({
            "doctype": "Capability Policy",
            "policy_name": f"{_TEST_PREFIX}role_target",
            "target_type": "Role",
            "target_role": _ROLE,
            "grant_type": "Capability",
            "capability": _CAPS["alpha"],
            "is_active": 1,
        })
        doc.insert(ignore_permissions=True)

        users = doc.get_target_users()
        self.assertIn(_USERS["user1"], users)
        # user2 does not have the test role
        self.assertNotIn(_USERS["user2"], users)

    def test_user_list_target(self):
        self._clean()
        doc = frappe.get_doc({
            "doctype": "Capability Policy",
            "policy_name": f"{_TEST_PREFIX}ulist",
            "target_type": "User List",
            "target_users": f"{_USERS['user1']},{_USERS['user2']}",
            "grant_type": "Capability",
            "capability": _CAPS["alpha"],
            "is_active": 1,
        })
        doc.insert(ignore_permissions=True)

        users = doc.get_target_users()
        self.assertIn(_USERS["user1"], users)
        self.assertIn(_USERS["user2"], users)


class TestApplyPolicies(unittest.TestCase):
    """Tests for policy_engine.apply_policies."""

    @classmethod
    def setUpClass(cls):
        _setup_policy_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_policy_data()

    def _clean(self):
        _clean_policies()
        _clean_user_caps()

    def test_apply_grants_capability(self):
        self._clean()

        frappe.get_doc({
            "doctype": "Capability Policy",
            "policy_name": f"{_TEST_PREFIX}apply_test",
            "target_type": "User List",
            "target_users": _USERS["user1"],
            "grant_type": "Capability",
            "capability": _CAPS["alpha"],
            "is_active": 1,
        }).insert(ignore_permissions=True)

        from caps.policy_engine import apply_policies
        summary = apply_policies()

        self.assertGreaterEqual(summary["applied"], 1)

        # Verify user1 has the capability
        doc = frappe.get_doc("User Capability", _USERS["user1"])
        cap_names = [r.capability for r in doc.direct_capabilities]
        self.assertIn(_CAPS["alpha"], cap_names)

        # Verify policy tag in notes
        for row in doc.direct_capabilities:
            if row.capability == _CAPS["alpha"]:
                self.assertIn(f"policy:{_TEST_PREFIX}apply_test", row.notes or "")

    def test_apply_skips_inactive(self):
        """Inactive policies should not result in any grants."""
        self._clean()

        frappe.get_doc({
            "doctype": "Capability Policy",
            "policy_name": f"{_TEST_PREFIX}skip_inactive",
            "target_type": "User List",
            "target_users": _USERS["user1"],
            "grant_type": "Capability",
            "capability": _CAPS["alpha"],
            "is_active": 0,
        }).insert(ignore_permissions=True)

        from caps.policy_engine import apply_policies
        summary = apply_policies()

        # Policy is inactive → not loaded at all → no grants
        self.assertEqual(summary["applied"], 0)
        self.assertFalse(frappe.db.exists("User Capability", _USERS["user1"]))

    def test_apply_skips_future(self):
        self._clean()

        frappe.get_doc({
            "doctype": "Capability Policy",
            "policy_name": f"{_TEST_PREFIX}skip_future",
            "target_type": "User List",
            "target_users": _USERS["user1"],
            "grant_type": "Capability",
            "capability": _CAPS["alpha"],
            "is_active": 1,
            "starts_on": add_days(now_datetime(), 30),
        }).insert(ignore_permissions=True)

        from caps.policy_engine import apply_policies
        summary = apply_policies()

        self.assertGreaterEqual(summary["skipped"], 1)

    def test_apply_idempotent(self):
        """Applying the same policy twice should not create duplicate grants."""
        self._clean()

        frappe.get_doc({
            "doctype": "Capability Policy",
            "policy_name": f"{_TEST_PREFIX}idempotent",
            "target_type": "User List",
            "target_users": _USERS["user1"],
            "grant_type": "Capability",
            "capability": _CAPS["alpha"],
            "is_active": 1,
        }).insert(ignore_permissions=True)

        from caps.policy_engine import apply_policies
        apply_policies()
        apply_policies()  # Second run

        doc = frappe.get_doc("User Capability", _USERS["user1"])
        alpha_count = sum(1 for r in doc.direct_capabilities if r.capability == _CAPS["alpha"])
        self.assertEqual(alpha_count, 1)


class TestExpirePolicies(unittest.TestCase):
    """Tests for policy_engine.expire_policies."""

    @classmethod
    def setUpClass(cls):
        _setup_policy_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_policy_data()

    def _clean(self):
        _clean_policies()
        _clean_user_caps()

    def test_expire_revokes_and_deactivates(self):
        self._clean()

        # Create and apply a policy that's already expired
        frappe.get_doc({
            "doctype": "Capability Policy",
            "policy_name": f"{_TEST_PREFIX}exp_test",
            "target_type": "User List",
            "target_users": _USERS["user1"],
            "grant_type": "Capability",
            "capability": _CAPS["alpha"],
            "is_active": 1,
            "starts_on": add_days(now_datetime(), -10),
            "ends_on": add_days(now_datetime(), -1),
        }).insert(ignore_permissions=True)

        # Manually grant as if policy had been applied
        from caps.policy_engine import _ensure_user_has_capability
        _ensure_user_has_capability(
            _USERS["user1"], _CAPS["alpha"],
            policy_name=f"{_TEST_PREFIX}exp_test",
        )

        # Now expire
        from caps.policy_engine import expire_policies
        summary = expire_policies()

        self.assertGreaterEqual(summary["expired"], 1)

        # Check policy is deactivated
        pol = frappe.get_doc("Capability Policy", f"{_TEST_PREFIX}exp_test")
        self.assertFalse(pol.is_active)


class TestPreviewPolicy(unittest.TestCase):
    """Tests for policy_engine.preview_policy."""

    @classmethod
    def setUpClass(cls):
        _setup_policy_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_policy_data()

    def _clean(self):
        _clean_policies()
        _clean_user_caps()

    def test_preview_shows_impact(self):
        self._clean()

        frappe.get_doc({
            "doctype": "Capability Policy",
            "policy_name": f"{_TEST_PREFIX}preview",
            "target_type": "User List",
            "target_users": f"{_USERS['user1']},{_USERS['user2']}",
            "grant_type": "Capability",
            "capability": _CAPS["alpha"],
            "is_active": 1,
        }).insert(ignore_permissions=True)

        from caps.policy_engine import preview_policy
        result = preview_policy(f"{_TEST_PREFIX}preview")

        self.assertEqual(result["target_users_count"], 2)
        self.assertEqual(result["capabilities_count"], 1)
        self.assertEqual(len(result["would_grant"]), 2)
        self.assertEqual(len(result["already_have"]), 0)

    def test_preview_existing_grants(self):
        self._clean()

        # Grant alpha to user1 first
        frappe.get_doc({
            "doctype": "User Capability",
            "user": _USERS["user1"],
            "direct_capabilities": [{"capability": _CAPS["alpha"]}],
        }).insert(ignore_permissions=True)

        frappe.get_doc({
            "doctype": "Capability Policy",
            "policy_name": f"{_TEST_PREFIX}prev_existing",
            "target_type": "User List",
            "target_users": f"{_USERS['user1']},{_USERS['user2']}",
            "grant_type": "Capability",
            "capability": _CAPS["alpha"],
            "is_active": 1,
        }).insert(ignore_permissions=True)

        from caps.policy_engine import preview_policy
        result = preview_policy(f"{_TEST_PREFIX}prev_existing")

        self.assertEqual(len(result["already_have"]), 1)
        self.assertEqual(len(result["would_grant"]), 1)
