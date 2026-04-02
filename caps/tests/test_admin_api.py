"""
CAPS — Phase 9-10 Tests: Admin API (Bulk Ops + Resolution Trace)
=================================================================

Tests for bulk_grant, bulk_revoke, clone_user_capabilities,
capability_usage_report, effective_permissions_matrix,
trace_capability, and explain_user.

Run with:
    bench --site dev.localhost run-tests --app caps \
        --module caps.tests.test_admin_api
"""

import json
import frappe
import unittest

_P = "capstest_adm_"

_CAPS = {
    "a": f"{_P}cap:alpha",
    "b": f"{_P}cap:bravo",
    "c": f"{_P}cap:charlie",
}

_USERS = {
    "u1": f"{_P}u1@test.local",
    "u2": f"{_P}u2@test.local",
    "u3": f"{_P}u3@test.local",
}

_GROUP = f"{_P}grp:staff"
_BUNDLE = f"{_P}bun:starter"


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

    for key, email in _USERS.items():
        if not frappe.db.exists("User", email):
            frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": "CAPSAdm",
                "last_name": key,
                "send_welcome_email": 0,
                "user_type": "System User",
            }).insert(ignore_permissions=True)

    # Permission Group
    frappe.get_doc({
        "doctype": "Permission Group",
        "__newname": _GROUP,
        "label": _GROUP,
        "group_capabilities": [{"capability": _CAPS["c"]}],
    }).insert(ignore_permissions=True)

    # Capability Bundle
    frappe.get_doc({
        "doctype": "Capability Bundle",
        "__newname": _BUNDLE,
        "label": _BUNDLE,
        "capabilities": [{"capability": _CAPS["a"]}, {"capability": _CAPS["b"]}],
    }).insert(ignore_permissions=True)

    frappe.db.commit()


def _teardown():
    from caps.utils.resolver import invalidate_all_caches
    invalidate_all_caches()

    for email in _USERS.values():
        if frappe.db.exists("User Capability", email):
            frappe.delete_doc("User Capability", email, force=True)

    if frappe.db.exists("Capability Bundle", _BUNDLE):
        frappe.delete_doc("Capability Bundle", _BUNDLE, force=True)

    if frappe.db.exists("Permission Group", _GROUP):
        frappe.delete_doc("Permission Group", _GROUP, force=True)

    for name in _CAPS.values():
        if frappe.db.exists("Capability", name):
            frappe.delete_doc("Capability", name, force=True)

    for email in _USERS.values():
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True)

    frappe.db.commit()


class TestBulkGrant(unittest.TestCase):
    """Test bulk_grant API."""

    @classmethod
    def setUpClass(cls):
        _setup()

    @classmethod
    def tearDownClass(cls):
        _teardown()

    def setUp(self):
        for email in _USERS.values():
            if frappe.db.exists("User Capability", email):
                frappe.delete_doc("User Capability", email, force=True)
        frappe.db.commit()
        from caps.utils.resolver import invalidate_all_caches
        invalidate_all_caches()

    def test_bulk_grant_multiple_users(self):
        """Grant capabilities to multiple users at once."""
        frappe.set_user("Administrator")
        from caps.api_admin import bulk_grant
        result = bulk_grant(
            users=json.dumps([_USERS["u1"], _USERS["u2"]]),
            capabilities=json.dumps([_CAPS["a"], _CAPS["b"]]),
        )
        self.assertEqual(result["granted"], 4)
        self.assertEqual(result["skipped"], 0)

    def test_bulk_grant_skips_duplicates(self):
        """Second call skips already-granted capabilities."""
        frappe.set_user("Administrator")
        from caps.api_admin import bulk_grant
        bulk_grant(
            users=json.dumps([_USERS["u1"]]),
            capabilities=json.dumps([_CAPS["a"]]),
        )
        result = bulk_grant(
            users=json.dumps([_USERS["u1"]]),
            capabilities=json.dumps([_CAPS["a"]]),
        )
        self.assertEqual(result["skipped"], 1)

    def test_bulk_grant_returns_errors_for_invalid_cap(self):
        """Invalid capability name creates an error entry."""
        frappe.set_user("Administrator")
        from caps.api_admin import bulk_grant
        result = bulk_grant(
            users=json.dumps([_USERS["u1"]]),
            capabilities=json.dumps(["__nonexistent_cap__"]),
        )
        self.assertTrue(len(result["errors"]) > 0)


class TestBulkRevoke(unittest.TestCase):
    """Test bulk_revoke API."""

    @classmethod
    def setUpClass(cls):
        _setup()

    @classmethod
    def tearDownClass(cls):
        _teardown()

    def setUp(self):
        for email in _USERS.values():
            if frappe.db.exists("User Capability", email):
                frappe.delete_doc("User Capability", email, force=True)
        frappe.db.commit()
        from caps.utils.resolver import invalidate_all_caches
        invalidate_all_caches()

    def test_bulk_revoke_removes_grants(self):
        """Revoke previously granted capabilities."""
        frappe.set_user("Administrator")
        from caps.api_admin import bulk_grant, bulk_revoke
        bulk_grant(
            users=json.dumps([_USERS["u1"]]),
            capabilities=json.dumps([_CAPS["a"], _CAPS["b"]]),
        )
        result = bulk_revoke(
            users=json.dumps([_USERS["u1"]]),
            capabilities=json.dumps([_CAPS["a"]]),
        )
        self.assertEqual(result["revoked"], 1)
        # Verify only b remains
        doc = frappe.get_doc("User Capability", _USERS["u1"])
        cap_names = [r.capability for r in doc.direct_capabilities]
        self.assertIn(_CAPS["b"], cap_names)
        self.assertNotIn(_CAPS["a"], cap_names)

    def test_bulk_revoke_skips_nonexistent(self):
        """Revoking something not granted counts as skipped."""
        frappe.set_user("Administrator")
        from caps.api_admin import bulk_revoke
        result = bulk_revoke(
            users=json.dumps([_USERS["u1"]]),
            capabilities=json.dumps([_CAPS["a"]]),
        )
        self.assertEqual(result["skipped"], 1)


class TestCloneCapabilities(unittest.TestCase):
    """Test clone_user_capabilities API."""

    @classmethod
    def setUpClass(cls):
        _setup()

    @classmethod
    def tearDownClass(cls):
        _teardown()

    def setUp(self):
        for email in _USERS.values():
            if frappe.db.exists("User Capability", email):
                frappe.delete_doc("User Capability", email, force=True)
        frappe.db.commit()
        from caps.utils.resolver import invalidate_all_caches
        invalidate_all_caches()

    def test_clone_direct_caps(self):
        """Clone direct capabilities from one user to another."""
        frappe.set_user("Administrator")
        from caps.api_admin import bulk_grant, clone_user_capabilities
        bulk_grant(
            users=json.dumps([_USERS["u1"]]),
            capabilities=json.dumps([_CAPS["a"], _CAPS["b"]]),
        )
        result = clone_user_capabilities(_USERS["u1"], _USERS["u2"], include_bundles=False)
        self.assertEqual(result["capabilities_cloned"], 2)

        doc = frappe.get_doc("User Capability", _USERS["u2"])
        cap_names = [r.capability for r in doc.direct_capabilities]
        self.assertIn(_CAPS["a"], cap_names)
        self.assertIn(_CAPS["b"], cap_names)

    def test_clone_with_bundles(self):
        """Clone including bundles."""
        frappe.set_user("Administrator")
        # Set up source user with bundle
        if not frappe.db.exists("User Capability", _USERS["u1"]):
            frappe.get_doc({"doctype": "User Capability", "user": _USERS["u1"]}).insert(ignore_permissions=True)
        doc = frappe.get_doc("User Capability", _USERS["u1"])
        doc.direct_capabilities = []
        doc.append("direct_capabilities", {"capability": _CAPS["a"]})
        doc.direct_bundles = []
        doc.append("direct_bundles", {"bundle": _BUNDLE})
        doc.save(ignore_permissions=True)
        frappe.db.commit()

        from caps.api_admin import clone_user_capabilities
        result = clone_user_capabilities(_USERS["u1"], _USERS["u3"], include_bundles=True)
        self.assertEqual(result["capabilities_cloned"], 1)
        self.assertEqual(result["bundles_cloned"], 1)

    def test_clone_skips_duplicates(self):
        """Cloning to user who already has the caps skips them."""
        frappe.set_user("Administrator")
        from caps.api_admin import bulk_grant, clone_user_capabilities
        bulk_grant(
            users=json.dumps([_USERS["u1"], _USERS["u2"]]),
            capabilities=json.dumps([_CAPS["a"]]),
        )
        result = clone_user_capabilities(_USERS["u1"], _USERS["u2"])
        self.assertEqual(result["skipped"], 1)


class TestUsageReport(unittest.TestCase):
    """Test capability_usage_report API."""

    @classmethod
    def setUpClass(cls):
        _setup()

    @classmethod
    def tearDownClass(cls):
        _teardown()

    def setUp(self):
        for email in _USERS.values():
            if frappe.db.exists("User Capability", email):
                frappe.delete_doc("User Capability", email, force=True)
        frappe.db.commit()
        from caps.utils.resolver import invalidate_all_caches
        invalidate_all_caches()

    def test_usage_report_counts(self):
        """Usage report returns correct user counts per capability."""
        frappe.set_user("Administrator")
        from caps.api_admin import bulk_grant, capability_usage_report
        bulk_grant(
            users=json.dumps([_USERS["u1"], _USERS["u2"]]),
            capabilities=json.dumps([_CAPS["a"]]),
        )
        bulk_grant(
            users=json.dumps([_USERS["u1"]]),
            capabilities=json.dumps([_CAPS["b"]]),
        )

        report = capability_usage_report()
        cap_map = {r["capability"]: r["user_count"] for r in report}
        self.assertEqual(cap_map.get(_CAPS["a"], 0), 2)
        self.assertEqual(cap_map.get(_CAPS["b"], 0), 1)


class TestEffectivePermissionsMatrix(unittest.TestCase):
    """Test effective_permissions_matrix API."""

    @classmethod
    def setUpClass(cls):
        _setup()

    @classmethod
    def tearDownClass(cls):
        _teardown()

    def setUp(self):
        for email in _USERS.values():
            if frappe.db.exists("User Capability", email):
                frappe.delete_doc("User Capability", email, force=True)
        frappe.db.commit()
        from caps.utils.resolver import invalidate_all_caches
        invalidate_all_caches()

    def test_matrix_returns_correct_sets(self):
        """Matrix returns correct effective capabilities per user."""
        frappe.set_user("Administrator")
        from caps.api_admin import bulk_grant, effective_permissions_matrix
        bulk_grant(
            users=json.dumps([_USERS["u1"]]),
            capabilities=json.dumps([_CAPS["a"], _CAPS["b"]]),
        )

        matrix = effective_permissions_matrix(users=json.dumps([_USERS["u1"]]))
        # matrix is a list of {user, total_count, capabilities}
        self.assertTrue(len(matrix) > 0)
        u1_entry = next((e for e in matrix if e["user"] == _USERS["u1"]), None)
        self.assertIsNotNone(u1_entry)
        u1_caps = set(u1_entry["capabilities"])
        self.assertIn(_CAPS["a"], u1_caps)
        self.assertIn(_CAPS["b"], u1_caps)


class TestTraceCapability(unittest.TestCase):
    """Test trace_capability API."""

    @classmethod
    def setUpClass(cls):
        _setup()

    @classmethod
    def tearDownClass(cls):
        _teardown()

    def setUp(self):
        for email in _USERS.values():
            if frappe.db.exists("User Capability", email):
                frappe.delete_doc("User Capability", email, force=True)
        frappe.db.commit()
        from caps.utils.resolver import invalidate_all_caches
        invalidate_all_caches()

    def test_trace_found_via_direct(self):
        """Trace shows capability found via direct channel."""
        frappe.set_user("Administrator")
        from caps.api_admin import bulk_grant, trace_capability
        bulk_grant(
            users=json.dumps([_USERS["u1"]]),
            capabilities=json.dumps([_CAPS["a"]]),
        )
        result = trace_capability(_USERS["u1"], _CAPS["a"])
        self.assertTrue(result["found"])
        self.assertTrue(result["channels"]["direct"]["provides"])

    def test_trace_not_found(self):
        """Trace shows capability NOT in resolved set."""
        frappe.set_user("Administrator")
        from caps.api_admin import trace_capability
        result = trace_capability(_USERS["u1"], _CAPS["a"])
        self.assertFalse(result["found"])

    def test_trace_via_group(self):
        """Trace shows capability found via group channel."""
        frappe.set_user("Administrator")
        # Add u1 to group via Permission Group Member child table
        grp = frappe.get_doc("Permission Group", _GROUP)
        grp.append("members", {"user": _USERS["u1"]})
        grp.save(ignore_permissions=True)
        frappe.db.commit()
        from caps.utils.resolver import invalidate_user_cache
        invalidate_user_cache(_USERS["u1"])

        from caps.api_admin import trace_capability
        result = trace_capability(_USERS["u1"], _CAPS["c"])
        self.assertTrue(result["found"])
        self.assertTrue(result["channels"]["groups"]["provides"])

        # Cleanup: remove from group
        grp.reload()
        grp.members = [m for m in grp.members if m.user != _USERS["u1"]]
        grp.save(ignore_permissions=True)
        frappe.db.commit()


class TestExplainUser(unittest.TestCase):
    """Test explain_user API."""

    @classmethod
    def setUpClass(cls):
        _setup()

    @classmethod
    def tearDownClass(cls):
        _teardown()

    def setUp(self):
        for email in _USERS.values():
            if frappe.db.exists("User Capability", email):
                frappe.delete_doc("User Capability", email, force=True)
        frappe.db.commit()
        from caps.utils.resolver import invalidate_all_caches
        invalidate_all_caches()

    def test_explain_shows_direct_caps(self):
        """explain_user lists directly granted capabilities."""
        frappe.set_user("Administrator")
        from caps.api_admin import bulk_grant, explain_user
        bulk_grant(
            users=json.dumps([_USERS["u1"]]),
            capabilities=json.dumps([_CAPS["a"]]),
        )
        result = explain_user(_USERS["u1"])
        self.assertIn(_CAPS["a"], result["channels"]["direct"])

    def test_explain_shows_group_caps(self):
        """explain_user lists group-sourced capabilities."""
        frappe.set_user("Administrator")
        # Add u1 to group via Permission Group Member
        grp = frappe.get_doc("Permission Group", _GROUP)
        grp.append("members", {"user": _USERS["u1"]})
        grp.save(ignore_permissions=True)
        frappe.db.commit()
        from caps.utils.resolver import invalidate_user_cache
        invalidate_user_cache(_USERS["u1"])

        from caps.api_admin import explain_user
        result = explain_user(_USERS["u1"])
        self.assertIn(_GROUP, result["channels"]["groups"])
        self.assertIn(_CAPS["c"], result["channels"]["groups"][_GROUP])
        self.assertIn(_CAPS["c"], result["final"])

        # Cleanup: remove from group
        grp.reload()
        grp.members = [m for m in grp.members if m.user != _USERS["u1"]]
        grp.save(ignore_permissions=True)
        frappe.db.commit()
