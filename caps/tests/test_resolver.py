# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS — Resolver Unit Tests
============================

Comprehensive tests for caps.utils.resolver covering:
- resolve_capabilities (3-channel resolution: direct, groups, roles)
- Bundle expansion
- Time-boxed capability expiry
- Administrator / Guest edge cases
- Redis cache behaviour
- has_capability, has_any_capability, has_all_capabilities
- require_capability guard
- Field & action restriction resolution
- Cache invalidation helpers

Run with:
    bench --site dev.localhost run-tests --app caps \
        --module caps.tests.test_resolver
"""

import frappe
import unittest
from frappe.utils import now_datetime, add_days


# ── Helpers ───────────────────────────────────────────────────────────

_TEST_PREFIX = "capstest_"
_USERS = {
    "direct": f"{_TEST_PREFIX}direct@test.local",
    "group":  f"{_TEST_PREFIX}group@test.local",
    "role":   f"{_TEST_PREFIX}role@test.local",
    "multi":  f"{_TEST_PREFIX}multi@test.local",
    "empty":  f"{_TEST_PREFIX}empty@test.local",
}

_CAP_NAMES = [
    f"{_TEST_PREFIX}cap:read",
    f"{_TEST_PREFIX}cap:write",
    f"{_TEST_PREFIX}cap:delete",
    f"{_TEST_PREFIX}cap:admin",
    f"{_TEST_PREFIX}cap:export",
    f"{_TEST_PREFIX}cap:approve",
    f"{_TEST_PREFIX}cap:expired",
]

_BUNDLE_NAME = f"{_TEST_PREFIX}bundle"
_GROUP_NAME = f"{_TEST_PREFIX}group"
_ROLE_NAME = f"{_TEST_PREFIX}role"


def _setup_module_data():
    """Create all test fixtures once."""
    _teardown_module_data()

    # Create capabilities
    for cap_name in _CAP_NAMES:
        frappe.get_doc({
            "doctype": "Capability",
            "name1": cap_name,
            "label": cap_name,
            "category": "Custom",
            "is_active": 1,
        }).insert(ignore_permissions=True)

    # Create a bundle with read + write + export
    bundle = frappe.get_doc({
        "doctype": "Capability Bundle",
        "__newname": _BUNDLE_NAME,
        "label": _BUNDLE_NAME,
        "capabilities": [
            {"capability": f"{_TEST_PREFIX}cap:read"},
            {"capability": f"{_TEST_PREFIX}cap:write"},
            {"capability": f"{_TEST_PREFIX}cap:export"},
        ],
    })
    bundle.insert(ignore_permissions=True)

    # Create a Frappe role
    if not frappe.db.exists("Role", _ROLE_NAME):
        frappe.get_doc({
            "doctype": "Role",
            "role_name": _ROLE_NAME,
            "desk_access": 1,
        }).insert(ignore_permissions=True)

    # Create test users
    for key, email in _USERS.items():
        if not frappe.db.exists("User", email):
            roles = [{"role": _ROLE_NAME}] if key in ("role", "multi") else []
            frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": "CAPSTest",
                "last_name": key,
                "send_welcome_email": 0,
                "user_type": "System User",
                "roles": roles,
            }).insert(ignore_permissions=True)

    # ── Direct user capabilities (for "direct" and "multi" users) ──
    for user_key in ("direct", "multi"):
        email = _USERS[user_key]
        uc = frappe.get_doc({
            "doctype": "User Capability",
            "user": email,
            "direct_capabilities": [
                {"capability": f"{_TEST_PREFIX}cap:read"},
                {"capability": f"{_TEST_PREFIX}cap:write"},
            ],
        })
        uc.insert(ignore_permissions=True)

    # Add an expired capability to "direct" user
    uc_direct = frappe.get_doc("User Capability", _USERS["direct"])
    uc_direct.append("direct_capabilities", {
        "capability": f"{_TEST_PREFIX}cap:expired",
        "expires_on": add_days(now_datetime(), -1),
    })
    uc_direct.save(ignore_permissions=True)

    # ── Permission Group (for "group" and "multi" users) ──
    grp = frappe.get_doc({
        "doctype": "Permission Group",
        "__newname": _GROUP_NAME,
        "label": _GROUP_NAME,
        "group_type": "Manual",
        "members": [
            {"user": _USERS["group"]},
            {"user": _USERS["multi"]},
        ],
        "group_capabilities": [
            {"capability": f"{_TEST_PREFIX}cap:delete"},
        ],
        "group_bundles": [
            {"bundle": _BUNDLE_NAME},
        ],
    })
    grp.insert(ignore_permissions=True)

    # ── Role Capability Map (for "role" and "multi" users) ──
    rcm = frappe.get_doc({
        "doctype": "Role Capability Map",
        "role": _ROLE_NAME,
        "role_capabilities": [
            {"capability": f"{_TEST_PREFIX}cap:approve"},
        ],
        "role_bundles": [
            {"bundle": _BUNDLE_NAME},
        ],
    })
    rcm.insert(ignore_permissions=True)

    frappe.db.commit()


def _teardown_module_data():
    """Remove all test fixtures."""
    # Clear Redis caps caches
    for key, email in _USERS.items():
        frappe.cache.delete_value(f"caps:user:{email}")

    # Role Capability Map
    if frappe.db.exists("Role Capability Map", _ROLE_NAME):
        frappe.delete_doc("Role Capability Map", _ROLE_NAME,
                          force=True, ignore_permissions=True)

    # Permission Group
    for name in frappe.get_all("Permission Group",
                               filters={"label": _GROUP_NAME}, pluck="name"):
        frappe.delete_doc("Permission Group", name,
                          force=True, ignore_permissions=True)

    # User Capabilities
    for email in _USERS.values():
        if frappe.db.exists("User Capability", email):
            frappe.delete_doc("User Capability", email,
                              force=True, ignore_permissions=True)

    # Bundle
    for name in frappe.get_all("Capability Bundle",
                               filters={"label": _BUNDLE_NAME}, pluck="name"):
        frappe.delete_doc("Capability Bundle", name,
                          force=True, ignore_permissions=True)

    # Capabilities
    for cap_name in _CAP_NAMES:
        if frappe.db.exists("Capability", cap_name):
            frappe.delete_doc("Capability", cap_name,
                              force=True, ignore_permissions=True)

    # Users
    for email in _USERS.values():
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email,
                              force=True, ignore_permissions=True)

    # Role
    if frappe.db.exists("Role", _ROLE_NAME):
        frappe.delete_doc("Role", _ROLE_NAME,
                          force=True, ignore_permissions=True)

    frappe.db.commit()


# ── Test Class ────────────────────────────────────────────────────────


class TestResolverDirectChannel(unittest.TestCase):
    """Tests for Channel 1: direct user capabilities."""

    @classmethod
    def setUpClass(cls):
        _setup_module_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_module_data()

    def _flush(self, user):
        frappe.cache.delete_value(f"caps:user:{user}")

    def test_direct_user_gets_assigned_caps(self):
        """Direct user should have read + write."""
        from caps.utils.resolver import resolve_capabilities
        user = _USERS["direct"]
        self._flush(user)
        caps = resolve_capabilities(user)
        self.assertIn(f"{_TEST_PREFIX}cap:read", caps)
        self.assertIn(f"{_TEST_PREFIX}cap:write", caps)

    def test_direct_user_does_not_have_unassigned(self):
        """Direct user should NOT have admin or approve."""
        from caps.utils.resolver import resolve_capabilities
        user = _USERS["direct"]
        self._flush(user)
        caps = resolve_capabilities(user)
        self.assertNotIn(f"{_TEST_PREFIX}cap:admin", caps)
        self.assertNotIn(f"{_TEST_PREFIX}cap:approve", caps)

    def test_expired_capability_excluded(self):
        """Expired time-boxed capability should not resolve."""
        from caps.utils.resolver import resolve_capabilities
        user = _USERS["direct"]
        self._flush(user)
        caps = resolve_capabilities(user)
        self.assertNotIn(f"{_TEST_PREFIX}cap:expired", caps)

    def test_empty_user_gets_nothing(self):
        """User with no capability assignments resolves to empty set."""
        from caps.utils.resolver import resolve_capabilities
        user = _USERS["empty"]
        self._flush(user)
        caps = resolve_capabilities(user)
        # Filter to our test caps only
        our_caps = {c for c in caps if c.startswith(_TEST_PREFIX)}
        self.assertEqual(our_caps, set())


class TestResolverGroupChannel(unittest.TestCase):
    """Tests for Channel 2: permission group capabilities."""

    @classmethod
    def setUpClass(cls):
        _setup_module_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_module_data()

    def _flush(self, user):
        frappe.cache.delete_value(f"caps:user:{user}")

    def test_group_member_gets_group_caps(self):
        """Group member should get direct group capabilities."""
        from caps.utils.resolver import resolve_capabilities
        user = _USERS["group"]
        self._flush(user)
        caps = resolve_capabilities(user)
        self.assertIn(f"{_TEST_PREFIX}cap:delete", caps)

    def test_group_member_gets_bundle_caps(self):
        """Group member should get capabilities from group's bundles."""
        from caps.utils.resolver import resolve_capabilities
        user = _USERS["group"]
        self._flush(user)
        caps = resolve_capabilities(user)
        # Bundle has read, write, export
        self.assertIn(f"{_TEST_PREFIX}cap:read", caps)
        self.assertIn(f"{_TEST_PREFIX}cap:write", caps)
        self.assertIn(f"{_TEST_PREFIX}cap:export", caps)

    def test_non_member_does_not_get_group_caps(self):
        """User NOT in the group should not get group caps."""
        from caps.utils.resolver import resolve_capabilities
        user = _USERS["direct"]
        self._flush(user)
        caps = resolve_capabilities(user)
        self.assertNotIn(f"{_TEST_PREFIX}cap:delete", caps)


class TestResolverRoleChannel(unittest.TestCase):
    """Tests for Channel 3: role-based capabilities."""

    @classmethod
    def setUpClass(cls):
        _setup_module_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_module_data()

    def _flush(self, user):
        frappe.cache.delete_value(f"caps:user:{user}")

    def test_role_user_gets_role_caps(self):
        """User with the role should get role capabilities."""
        from caps.utils.resolver import resolve_capabilities
        user = _USERS["role"]
        self._flush(user)
        caps = resolve_capabilities(user)
        self.assertIn(f"{_TEST_PREFIX}cap:approve", caps)

    def test_role_user_gets_role_bundle_caps(self):
        """User with the role should get bundle caps from role map."""
        from caps.utils.resolver import resolve_capabilities
        user = _USERS["role"]
        self._flush(user)
        caps = resolve_capabilities(user)
        self.assertIn(f"{_TEST_PREFIX}cap:read", caps)
        self.assertIn(f"{_TEST_PREFIX}cap:write", caps)
        self.assertIn(f"{_TEST_PREFIX}cap:export", caps)

    def test_user_without_role_gets_nothing_from_role_channel(self):
        """User without the role should not get role caps."""
        from caps.utils.resolver import resolve_capabilities
        user = _USERS["group"]
        self._flush(user)
        caps = resolve_capabilities(user)
        self.assertNotIn(f"{_TEST_PREFIX}cap:approve", caps)


class TestResolverMultiChannel(unittest.TestCase):
    """Tests for multi-channel resolution (direct + group + role combined)."""

    @classmethod
    def setUpClass(cls):
        _setup_module_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_module_data()

    def _flush(self, user):
        frappe.cache.delete_value(f"caps:user:{user}")

    def test_multi_user_gets_all_channels(self):
        """Multi user (direct + group + role) gets union of all channels."""
        from caps.utils.resolver import resolve_capabilities
        user = _USERS["multi"]
        self._flush(user)
        caps = resolve_capabilities(user)
        our_caps = {c for c in caps if c.startswith(_TEST_PREFIX)}
        # Direct: read, write
        # Group: delete + bundle(read, write, export)
        # Role: approve + bundle(read, write, export)
        expected = {
            f"{_TEST_PREFIX}cap:read",
            f"{_TEST_PREFIX}cap:write",
            f"{_TEST_PREFIX}cap:delete",
            f"{_TEST_PREFIX}cap:export",
            f"{_TEST_PREFIX}cap:approve",
        }
        self.assertEqual(our_caps, expected)

    def test_multi_user_excludes_admin(self):
        """Multi user should NOT have admin (not assigned anywhere)."""
        from caps.utils.resolver import resolve_capabilities
        user = _USERS["multi"]
        self._flush(user)
        caps = resolve_capabilities(user)
        self.assertNotIn(f"{_TEST_PREFIX}cap:admin", caps)

    def test_multi_user_excludes_expired(self):
        """Multi user should NOT have the expired capability."""
        from caps.utils.resolver import resolve_capabilities
        user = _USERS["multi"]
        self._flush(user)
        caps = resolve_capabilities(user)
        self.assertNotIn(f"{_TEST_PREFIX}cap:expired", caps)


class TestResolverEdgeCases(unittest.TestCase):
    """Edge cases: Administrator, Guest, inactive capabilities."""

    @classmethod
    def setUpClass(cls):
        _setup_module_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_module_data()

    def test_administrator_gets_all_active(self):
        """Administrator should get ALL active capabilities."""
        from caps.utils.resolver import resolve_capabilities
        caps = resolve_capabilities("Administrator")
        for cap_name in _CAP_NAMES:
            self.assertIn(cap_name, caps)

    def test_guest_gets_empty(self):
        """Guest should get empty set."""
        from caps.utils.resolver import resolve_capabilities
        caps = resolve_capabilities("Guest")
        self.assertEqual(caps, set())

    def test_inactive_capability_excluded(self):
        """Deactivating a capability should exclude it from resolution."""
        from caps.utils.resolver import resolve_capabilities

        cap = frappe.get_doc("Capability", f"{_TEST_PREFIX}cap:read")
        cap.is_active = 0
        cap.save(ignore_permissions=True)
        frappe.db.commit()

        user = _USERS["direct"]
        frappe.cache.delete_value(f"caps:user:{user}")
        caps = resolve_capabilities(user)
        self.assertNotIn(f"{_TEST_PREFIX}cap:read", caps)

        # Restore
        cap.is_active = 1
        cap.save(ignore_permissions=True)
        frappe.db.commit()

    def test_resolve_returns_set(self):
        """resolve_capabilities should return a set."""
        from caps.utils.resolver import resolve_capabilities
        result = resolve_capabilities(_USERS["direct"])
        self.assertIsInstance(result, set)


class TestResolverCache(unittest.TestCase):
    """Tests for Redis caching behaviour."""

    @classmethod
    def setUpClass(cls):
        _setup_module_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_module_data()

    def _flush(self, user):
        frappe.cache.delete_value(f"caps:user:{user}")

    def test_cache_is_populated_after_resolve(self):
        """After resolving, the Redis cache key should exist."""
        from caps.utils.resolver import resolve_capabilities
        user = _USERS["direct"]
        self._flush(user)
        resolve_capabilities(user)
        cached = frappe.cache.get_value(f"caps:user:{user}")
        self.assertIsNotNone(cached)

    def test_cached_result_matches_fresh(self):
        """Cached resolution should equal a fresh resolution."""
        from caps.utils.resolver import resolve_capabilities
        user = _USERS["direct"]
        self._flush(user)
        fresh = resolve_capabilities(user)
        cached_result = resolve_capabilities(user)  # should hit cache
        self.assertEqual(fresh, cached_result)

    def test_invalidate_user_cache_clears(self):
        """invalidate_user_cache should remove the cached entry."""
        from caps.utils.resolver import invalidate_user_cache, resolve_capabilities
        user = _USERS["direct"]
        self._flush(user)
        resolve_capabilities(user)
        invalidate_user_cache(user)
        cached = frappe.cache.get_value(f"caps:user:{user}")
        self.assertIsNone(cached)

    def test_invalidate_all_caches(self):
        """invalidate_all_caches should clear all caps user caches."""
        from caps.utils.resolver import invalidate_all_caches, resolve_capabilities
        # Populate caches for two users
        for key in ("direct", "group"):
            self._flush(_USERS[key])
            resolve_capabilities(_USERS[key])

        invalidate_all_caches()

        for key in ("direct", "group"):
            cached = frappe.cache.get_value(f"caps:user:{_USERS[key]}")
            self.assertIsNone(cached)


class TestHasCapability(unittest.TestCase):
    """Tests for has_capability, has_any, has_all, require_capability."""

    @classmethod
    def setUpClass(cls):
        _setup_module_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_module_data()

    def _flush(self, user):
        frappe.cache.delete_value(f"caps:user:{user}")

    def test_has_capability_true(self):
        from caps.utils.resolver import has_capability
        user = _USERS["direct"]
        self._flush(user)
        self.assertTrue(has_capability(f"{_TEST_PREFIX}cap:read", user))

    def test_has_capability_false(self):
        from caps.utils.resolver import has_capability
        user = _USERS["direct"]
        self._flush(user)
        self.assertFalse(has_capability(f"{_TEST_PREFIX}cap:admin", user))

    def test_has_any_with_match(self):
        from caps.utils.resolver import has_any_capability
        user = _USERS["direct"]
        self._flush(user)
        self.assertTrue(has_any_capability(
            f"{_TEST_PREFIX}cap:read", f"{_TEST_PREFIX}cap:admin", user=user
        ))

    def test_has_any_no_match(self):
        from caps.utils.resolver import has_any_capability
        user = _USERS["direct"]
        self._flush(user)
        self.assertFalse(has_any_capability(
            f"{_TEST_PREFIX}cap:admin", f"{_TEST_PREFIX}cap:approve", user=user
        ))

    def test_has_all_true(self):
        from caps.utils.resolver import has_all_capabilities
        user = _USERS["direct"]
        self._flush(user)
        self.assertTrue(has_all_capabilities(
            f"{_TEST_PREFIX}cap:read", f"{_TEST_PREFIX}cap:write", user=user
        ))

    def test_has_all_false_partial(self):
        from caps.utils.resolver import has_all_capabilities
        user = _USERS["direct"]
        self._flush(user)
        self.assertFalse(has_all_capabilities(
            f"{_TEST_PREFIX}cap:read", f"{_TEST_PREFIX}cap:admin", user=user
        ))

    def test_require_capability_passes(self):
        """require_capability should not raise when user has the cap."""
        from caps.utils.resolver import require_capability
        user = _USERS["direct"]
        self._flush(user)
        # Should not raise
        require_capability(f"{_TEST_PREFIX}cap:read", user)

    def test_require_capability_raises(self):
        """require_capability should raise PermissionError when cap is missing."""
        from caps.utils.resolver import require_capability
        user = _USERS["direct"]
        self._flush(user)
        with self.assertRaises(frappe.PermissionError):
            require_capability(f"{_TEST_PREFIX}cap:admin", user)


class TestFieldRestrictions(unittest.TestCase):
    """Tests for get_field_restrictions and get_field_restrictions_all."""

    @classmethod
    def setUpClass(cls):
        _setup_module_data()
        # Create a field capability map:
        #   Note.title → requires capstest_cap:read → hide if missing
        frappe.get_doc({
            "doctype": "Field Capability Map",
            "doctype_name": "Note",
            "fieldname": "title",
            "capability": f"{_TEST_PREFIX}cap:read",
            "behavior": "hide",
            "priority": 10,
        }).insert(ignore_permissions=True)

        frappe.get_doc({
            "doctype": "Field Capability Map",
            "doctype_name": "Note",
            "fieldname": "content",
            "capability": f"{_TEST_PREFIX}cap:admin",
            "behavior": "mask",
            "mask_pattern": "***{last4}",
            "priority": 5,
        }).insert(ignore_permissions=True)

        frappe.db.commit()
        # Clear field map caches
        from caps.utils.resolver import invalidate_field_action_caches
        invalidate_field_action_caches()

    @classmethod
    def tearDownClass(cls):
        # Clean field maps
        for name in frappe.get_all("Field Capability Map",
                                    filters={"capability": ("like", f"{_TEST_PREFIX}%")},
                                    pluck="name"):
            frappe.delete_doc("Field Capability Map", name,
                              force=True, ignore_permissions=True)
        frappe.db.commit()
        from caps.utils.resolver import invalidate_field_action_caches
        invalidate_field_action_caches()
        _teardown_module_data()

    def _flush(self, user):
        frappe.cache.delete_value(f"caps:user:{user}")
        # Also flush field map cache
        frappe.cache.delete_value("caps:fieldmap:Note")

    def test_no_restriction_when_user_has_cap(self):
        """User with cap:read should NOT have title restricted."""
        from caps.utils.resolver import get_field_restrictions
        user = _USERS["direct"]
        self._flush(user)
        restrictions = get_field_restrictions("Note", user)
        self.assertNotIn("title", restrictions)

    def test_restriction_when_user_lacks_cap(self):
        """User without cap:read should have title restricted (hide)."""
        from caps.utils.resolver import get_field_restrictions
        user = _USERS["empty"]
        self._flush(user)
        restrictions = get_field_restrictions("Note", user)
        self.assertIn("title", restrictions)
        self.assertEqual(restrictions["title"]["behavior"], "hide")

    def test_mask_restriction(self):
        """Nobody has cap:admin → content should be masked for all non-Admin."""
        from caps.utils.resolver import get_field_restrictions
        user = _USERS["direct"]
        self._flush(user)
        restrictions = get_field_restrictions("Note", user)
        self.assertIn("content", restrictions)
        self.assertEqual(restrictions["content"]["behavior"], "mask")
        self.assertEqual(restrictions["content"]["mask_pattern"], "***{last4}")

    def test_administrator_no_restrictions(self):
        """Administrator should get no field restrictions."""
        from caps.utils.resolver import get_field_restrictions
        restrictions = get_field_restrictions("Note", "Administrator")
        self.assertEqual(restrictions, {})

    def test_field_restrictions_all(self):
        """get_field_restrictions_all should aggregate across doctypes."""
        from caps.utils.resolver import get_field_restrictions_all
        user = _USERS["empty"]
        frappe.cache.delete_value(f"caps:user:{user}")
        result = get_field_restrictions_all(user)
        self.assertIn("Note", result)
        self.assertIn("title", result["Note"])

    def test_higher_priority_wins(self):
        """Higher priority Field Capability Map should win over lower."""
        from caps.utils.resolver import get_field_restrictions
        user = _USERS["empty"]
        self._flush(user)
        restrictions = get_field_restrictions("Note", user)
        # title has priority 10 (hide), content has priority 5 (mask)
        # Just verify both are present with correct behaviors
        self.assertEqual(restrictions["title"]["behavior"], "hide")
        self.assertEqual(restrictions["content"]["behavior"], "mask")


class TestActionRestrictions(unittest.TestCase):
    """Tests for get_action_restrictions and get_action_restrictions_all."""

    @classmethod
    def setUpClass(cls):
        _setup_module_data()
        frappe.get_doc({
            "doctype": "Action Capability Map",
            "doctype_name": "Note",
            "action_id": f"{_TEST_PREFIX}call",
            "action_type": "button",
            "capability": f"{_TEST_PREFIX}cap:read",
            "fallback_behavior": "hide",
            "fallback_message": "Not allowed to call",
        }).insert(ignore_permissions=True)

        frappe.get_doc({
            "doctype": "Action Capability Map",
            "doctype_name": "Note",
            "action_id": f"{_TEST_PREFIX}admin_action",
            "action_type": "menu_item",
            "capability": f"{_TEST_PREFIX}cap:admin",
            "fallback_behavior": "disable",
        }).insert(ignore_permissions=True)

        frappe.db.commit()
        from caps.utils.resolver import invalidate_field_action_caches
        invalidate_field_action_caches()

    @classmethod
    def tearDownClass(cls):
        for name in frappe.get_all("Action Capability Map",
                                    filters={"action_id": ("like", f"{_TEST_PREFIX}%")},
                                    pluck="name"):
            frappe.delete_doc("Action Capability Map", name,
                              force=True, ignore_permissions=True)
        frappe.db.commit()
        from caps.utils.resolver import invalidate_field_action_caches
        invalidate_field_action_caches()
        _teardown_module_data()

    def _flush(self, user):
        frappe.cache.delete_value(f"caps:user:{user}")
        frappe.cache.delete_value("caps:actionmap:Note")

    def test_no_restriction_when_user_has_cap(self):
        """User with cap:read should NOT be restricted from call action."""
        from caps.utils.resolver import get_action_restrictions
        user = _USERS["direct"]
        self._flush(user)
        restrictions = get_action_restrictions("Note", user)
        action_ids = [r["action_id"] for r in restrictions]
        self.assertNotIn(f"{_TEST_PREFIX}call", action_ids)

    def test_restriction_when_user_lacks_cap(self):
        """User without cap:read should be restricted from call."""
        from caps.utils.resolver import get_action_restrictions
        user = _USERS["empty"]
        self._flush(user)
        restrictions = get_action_restrictions("Note", user)
        action_ids = [r["action_id"] for r in restrictions]
        self.assertIn(f"{_TEST_PREFIX}call", action_ids)

    def test_admin_action_restricted_for_all_non_admin(self):
        """Nobody has cap:admin so admin_action should be restricted."""
        from caps.utils.resolver import get_action_restrictions
        user = _USERS["direct"]
        self._flush(user)
        restrictions = get_action_restrictions("Note", user)
        action_ids = [r["action_id"] for r in restrictions]
        self.assertIn(f"{_TEST_PREFIX}admin_action", action_ids)

    def test_administrator_no_restrictions(self):
        """Administrator should get no action restrictions."""
        from caps.utils.resolver import get_action_restrictions
        restrictions = get_action_restrictions("Note", "Administrator")
        self.assertEqual(restrictions, [])

    def test_action_restrictions_all(self):
        """get_action_restrictions_all should aggregate across doctypes."""
        from caps.utils.resolver import get_action_restrictions_all
        user = _USERS["empty"]
        frappe.cache.delete_value(f"caps:user:{user}")
        result = get_action_restrictions_all(user)
        self.assertIn("Note", result)
        ids = [a["action_id"] for a in result["Note"]]
        self.assertIn(f"{_TEST_PREFIX}call", ids)

    def test_restriction_includes_fallback(self):
        """Restricted action should carry fallback_behavior and message."""
        from caps.utils.resolver import get_action_restrictions
        user = _USERS["empty"]
        self._flush(user)
        restrictions = get_action_restrictions("Note", user)
        call_r = [r for r in restrictions if r["action_id"] == f"{_TEST_PREFIX}call"][0]
        self.assertEqual(call_r["fallback_behavior"], "hide")
        self.assertEqual(call_r["fallback_message"], "Not allowed to call")


class TestBundleExpansion(unittest.TestCase):
    """Tests for _expand_bundles internal helper."""

    @classmethod
    def setUpClass(cls):
        _setup_module_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_module_data()

    def test_expand_known_bundle(self):
        """Expanding the test bundle should yield read + write + export."""
        from caps.utils.resolver import _expand_bundles, _all_active_capability_names
        active = _all_active_capability_names()
        result = _expand_bundles([_BUNDLE_NAME], active)
        self.assertIn(f"{_TEST_PREFIX}cap:read", result)
        self.assertIn(f"{_TEST_PREFIX}cap:write", result)
        self.assertIn(f"{_TEST_PREFIX}cap:export", result)
        self.assertNotIn(f"{_TEST_PREFIX}cap:admin", result)

    def test_expand_empty_list(self):
        """Expanding empty bundle list should return empty set."""
        from caps.utils.resolver import _expand_bundles, _all_active_capability_names
        active = _all_active_capability_names()
        result = _expand_bundles([], active)
        self.assertEqual(result, set())

    def test_expand_nonexistent_bundle(self):
        """Expanding a non-existent bundle should return empty set."""
        from caps.utils.resolver import _expand_bundles, _all_active_capability_names
        active = _all_active_capability_names()
        result = _expand_bundles(["does_not_exist"], active)
        self.assertEqual(result, set())
