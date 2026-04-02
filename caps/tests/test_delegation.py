"""
CAPS — Delegation Tests
========================

Tests for delegation API (caps.api_delegation):
 - delegate_capability
 - revoke_delegated
 - get_delegatable_capabilities
 - get_my_delegations
 - settings toggles

Prefix: capstest_dlg_

Run with:
    bench --site dev.localhost run-tests --app caps \
        --module caps.tests.test_delegation
"""

import frappe
import unittest
from frappe.utils import now_datetime, add_days

_TEST_PREFIX = "capstest_dlg_"

_CAPS = {
    "delegatable": f"{_TEST_PREFIX}cap:delegatable",
    "nondelegatable": f"{_TEST_PREFIX}cap:nondelegatable",
    "inactive": f"{_TEST_PREFIX}cap:inactive",
}

_USERS = {
    "manager": f"{_TEST_PREFIX}manager@test.local",
    "target": f"{_TEST_PREFIX}target@test.local",
    "other": f"{_TEST_PREFIX}other@test.local",
}


def _setup_delegation_data():
    _teardown_delegation_data()

    # Ensure delegation is enabled
    frappe.db.set_single_value("CAPS Settings", "enable_delegation", 1)
    frappe.db.set_single_value("CAPS Settings", "require_delegation_reason", 0)
    _clear_settings_cache()

    # Create capabilities
    frappe.get_doc({
        "doctype": "Capability",
        "name1": _CAPS["delegatable"],
        "label": "Delegatable Cap",
        "category": "Custom",
        "is_active": 1,
        "is_delegatable": 1,
    }).insert(ignore_permissions=True)

    frappe.get_doc({
        "doctype": "Capability",
        "name1": _CAPS["nondelegatable"],
        "label": "NonDelegatable Cap",
        "category": "Custom",
        "is_active": 1,
        "is_delegatable": 0,
    }).insert(ignore_permissions=True)

    frappe.get_doc({
        "doctype": "Capability",
        "name1": _CAPS["inactive"],
        "label": "Inactive Cap",
        "category": "Custom",
        "is_active": 0,
        "is_delegatable": 1,
    }).insert(ignore_permissions=True)

    # Create users
    for key, email in _USERS.items():
        if not frappe.db.exists("User", email):
            u = frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": "CAPSDlg",
                "last_name": key,
                "send_welcome_email": 0,
                "user_type": "System User",
            })
            u.insert(ignore_permissions=True)

    # Give CAPS Manager role to manager user
    mgr = frappe.get_doc("User", _USERS["manager"])
    if not any(r.role == "CAPS Manager" for r in mgr.roles):
        mgr.append("roles", {"role": "CAPS Manager"})
        mgr.save(ignore_permissions=True)

    # Grant delegatable + nondelegatable to manager
    frappe.get_doc({
        "doctype": "User Capability",
        "user": _USERS["manager"],
        "direct_capabilities": [
            {"capability": _CAPS["delegatable"]},
            {"capability": _CAPS["nondelegatable"]},
        ],
    }).insert(ignore_permissions=True)

    frappe.db.commit()


def _teardown_delegation_data():
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

    for email in _USERS.values():
        _safe_delete_user(email)

    _clear_settings_cache()
    frappe.db.commit()


def _safe_delete_user(email):
    """Delete user, handling linked docs from other apps (e.g. Gameplan)."""
    if not frappe.db.exists("User", email):
        return
    try:
        frappe.delete_doc("User", email, force=True, ignore_permissions=True)
    except Exception:
        # Linked docs (GP User Profile etc.) may block deletion
        # Clean up linked docs first, then retry
        try:
            for dt in ("GP User Profile",):
                for name in frappe.get_all(dt, filters={"user": email}, pluck="name"):
                    frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        except Exception:
            pass  # Best-effort cleanup


def _clear_settings_cache():
    """Clear all CAPS Settings caches."""
    if hasattr(frappe.local, "_caps_settings"):
        del frappe.local._caps_settings
    frappe.clear_document_cache("CAPS Settings", "CAPS Settings")


def _flush(user):
    frappe.cache.delete_value(f"caps:user:{user}")


def _as_user(email):
    """Context helper: sets frappe.session.user then restores."""
    class _Ctx:
        def __init__(self):
            self.old = frappe.session.user
        def __enter__(self):
            frappe.set_user(email)
            return self
        def __exit__(self, *args):
            frappe.set_user(self.old)
    return _Ctx()


# ── Tests ─────────────────────────────────────────────────────────────


class TestDelegateCapability(unittest.TestCase):
    """Tests for caps.api_delegation.delegate_capability."""

    @classmethod
    def setUpClass(cls):
        _setup_delegation_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_delegation_data()

    def _reset_target(self):
        """Remove user capability for target so each test starts clean."""
        if frappe.db.exists("User Capability", _USERS["target"]):
            frappe.delete_doc("User Capability", _USERS["target"],
                              force=True, ignore_permissions=True)
        _flush(_USERS["target"])

    def test_successful_delegation(self):
        self._reset_target()
        from caps.api_delegation import delegate_capability
        _flush(_USERS["manager"])

        with _as_user(_USERS["manager"]):
            result = delegate_capability(
                user=_USERS["target"],
                capability=_CAPS["delegatable"],
                reason="Team access",
            )

        self.assertEqual(result["status"], "delegated")

        # Verify grant exists with delegated_by
        doc = frappe.get_doc("User Capability", _USERS["target"])
        row = doc.direct_capabilities[0]
        self.assertEqual(row.capability, _CAPS["delegatable"])
        self.assertEqual(row.delegated_by, _USERS["manager"])

    def test_delegate_non_delegatable_fails(self):
        self._reset_target()
        from caps.api_delegation import delegate_capability
        _flush(_USERS["manager"])

        with _as_user(_USERS["manager"]):
            with self.assertRaises(frappe.exceptions.ValidationError):
                delegate_capability(
                    user=_USERS["target"],
                    capability=_CAPS["nondelegatable"],
                )

    def test_delegate_inactive_fails(self):
        self._reset_target()
        from caps.api_delegation import delegate_capability
        _flush(_USERS["manager"])

        with _as_user(_USERS["manager"]):
            with self.assertRaises(frappe.exceptions.ValidationError):
                delegate_capability(
                    user=_USERS["target"],
                    capability=_CAPS["inactive"],
                )

    def test_delegate_unheld_cap_fails(self):
        """Manager can't delegate a cap they don't hold."""
        self._reset_target()
        from caps.api_delegation import delegate_capability
        _flush(_USERS["other"])

        # Other user doesn't have CAPS Manager role, but let's give it
        other_user = frappe.get_doc("User", _USERS["other"])
        if not any(r.role == "CAPS Manager" for r in other_user.roles):
            other_user.append("roles", {"role": "CAPS Manager"})
            other_user.save(ignore_permissions=True)

        with _as_user(_USERS["other"]):
            _flush(_USERS["other"])
            with self.assertRaises(frappe.exceptions.ValidationError):
                delegate_capability(
                    user=_USERS["target"],
                    capability=_CAPS["delegatable"],
                )

    def test_self_delegation_fails(self):
        from caps.api_delegation import delegate_capability
        _flush(_USERS["manager"])

        with _as_user(_USERS["manager"]):
            with self.assertRaises(frappe.exceptions.ValidationError):
                delegate_capability(
                    user=_USERS["manager"],
                    capability=_CAPS["delegatable"],
                )

    def test_duplicate_delegation_fails(self):
        self._reset_target()
        from caps.api_delegation import delegate_capability
        _flush(_USERS["manager"])

        with _as_user(_USERS["manager"]):
            delegate_capability(
                user=_USERS["target"],
                capability=_CAPS["delegatable"],
            )
            with self.assertRaises(frappe.exceptions.ValidationError):
                delegate_capability(
                    user=_USERS["target"],
                    capability=_CAPS["delegatable"],
                )

    def test_delegation_disabled_in_settings(self):
        self._reset_target()
        from caps.api_delegation import delegate_capability
        _flush(_USERS["manager"])

        # Disable delegation
        frappe.db.set_single_value("CAPS Settings", "enable_delegation", 0)
        _clear_settings_cache()

        try:
            with _as_user(_USERS["manager"]):
                with self.assertRaises(frappe.exceptions.ValidationError):
                    delegate_capability(
                        user=_USERS["target"],
                        capability=_CAPS["delegatable"],
                    )
        finally:
            frappe.db.set_single_value("CAPS Settings", "enable_delegation", 1)
            _clear_settings_cache()

    def test_delegation_requires_reason(self):
        self._reset_target()
        from caps.api_delegation import delegate_capability
        _flush(_USERS["manager"])

        frappe.db.set_single_value("CAPS Settings", "require_delegation_reason", 1)
        _clear_settings_cache()

        try:
            with _as_user(_USERS["manager"]):
                with self.assertRaises(frappe.exceptions.ValidationError):
                    delegate_capability(
                        user=_USERS["target"],
                        capability=_CAPS["delegatable"],
                    )
        finally:
            frappe.db.set_single_value("CAPS Settings", "require_delegation_reason", 0)
            _clear_settings_cache()


class TestRevokeDelegated(unittest.TestCase):
    """Tests for caps.api_delegation.revoke_delegated."""

    @classmethod
    def setUpClass(cls):
        _setup_delegation_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_delegation_data()

    def _delegate_first(self):
        if frappe.db.exists("User Capability", _USERS["target"]):
            frappe.delete_doc("User Capability", _USERS["target"],
                              force=True, ignore_permissions=True)
        _flush(_USERS["target"])
        _flush(_USERS["manager"])
        from caps.api_delegation import delegate_capability
        with _as_user(_USERS["manager"]):
            delegate_capability(
                user=_USERS["target"],
                capability=_CAPS["delegatable"],
            )

    def test_revoke_own_delegation(self):
        self._delegate_first()
        from caps.api_delegation import revoke_delegated
        _flush(_USERS["manager"])

        with _as_user(_USERS["manager"]):
            result = revoke_delegated(
                user=_USERS["target"],
                capability=_CAPS["delegatable"],
            )

        self.assertEqual(result["status"], "revoked")

        doc = frappe.get_doc("User Capability", _USERS["target"])
        self.assertEqual(len(doc.direct_capabilities), 0)

    def test_admin_can_revoke_any_delegation(self):
        self._delegate_first()
        from caps.api_delegation import revoke_delegated

        # Admin (Administrator) can revoke anyone's delegation
        with _as_user("Administrator"):
            result = revoke_delegated(
                user=_USERS["target"],
                capability=_CAPS["delegatable"],
            )

        self.assertEqual(result["status"], "revoked")

    def test_revoke_nonexistent_fails(self):
        from caps.api_delegation import revoke_delegated

        with _as_user("Administrator"):
            with self.assertRaises(frappe.exceptions.ValidationError):
                revoke_delegated(
                    user=_USERS["target"],
                    capability="nonexistent_cap",
                )


class TestGetDelegatableCapabilities(unittest.TestCase):
    """Tests for caps.api_delegation.get_delegatable_capabilities."""

    @classmethod
    def setUpClass(cls):
        _setup_delegation_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_delegation_data()

    def test_returns_only_delegatable_held_caps(self):
        from caps.api_delegation import get_delegatable_capabilities
        _flush(_USERS["manager"])

        with _as_user(_USERS["manager"]):
            result = get_delegatable_capabilities()

        names = [r["name"] for r in result]
        self.assertIn(_CAPS["delegatable"], names)
        self.assertNotIn(_CAPS["nondelegatable"], names)
        self.assertNotIn(_CAPS["inactive"], names)


class TestGetMyDelegations(unittest.TestCase):
    """Tests for caps.api_delegation.get_my_delegations."""

    @classmethod
    def setUpClass(cls):
        _setup_delegation_data()
        # Create a delegation
        if frappe.db.exists("User Capability", _USERS["target"]):
            frappe.delete_doc("User Capability", _USERS["target"],
                              force=True, ignore_permissions=True)
        _flush(_USERS["target"])
        _flush(_USERS["manager"])
        from caps.api_delegation import delegate_capability
        frappe.set_user(_USERS["manager"])
        delegate_capability(
            user=_USERS["target"],
            capability=_CAPS["delegatable"],
        )
        frappe.set_user("Administrator")

    @classmethod
    def tearDownClass(cls):
        _teardown_delegation_data()

    def test_returns_delegations(self):
        from caps.api_delegation import get_my_delegations
        with _as_user(_USERS["manager"]):
            result = get_my_delegations()

        self.assertTrue(len(result) >= 1)
        caps = [r["capability"] for r in result]
        self.assertIn(_CAPS["delegatable"], caps)
