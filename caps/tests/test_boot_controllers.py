"""
CAPS — Boot Session & DocType Controller Tests
=================================================

Tests for caps.boot.boot_session and DocType controller validations.

Run with:
    bench --site dev.localhost run-tests --app caps \
        --module caps.tests.test_boot_controllers
"""

import frappe
import unittest

_TEST_PREFIX = "capstest_bc_"

_CAP_NAMES = [
    f"{_TEST_PREFIX}cap:one",
    f"{_TEST_PREFIX}cap:two",
]

_USERS = {
    "u1": f"{_TEST_PREFIX}u1@test.local",
}


def _setup_bc_data():
    _teardown_bc_data()

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
                "first_name": "CAPSBoot",
                "last_name": key,
                "send_welcome_email": 0,
                "user_type": "System User",
            }).insert(ignore_permissions=True)

    frappe.get_doc({
        "doctype": "User Capability",
        "user": _USERS["u1"],
        "direct_capabilities": [
            {"capability": f"{_TEST_PREFIX}cap:one"},
        ],
    }).insert(ignore_permissions=True)

    frappe.db.commit()


def _teardown_bc_data():
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


# ── Boot Session Tests ────────────────────────────────────────────────


class TestBootSession(unittest.TestCase):
    """Tests for caps.boot.boot_session."""

    @classmethod
    def setUpClass(cls):
        _setup_bc_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_bc_data()

    def test_boot_injects_caps_key(self):
        """boot_session should add 'caps' key to bootinfo."""
        from caps.boot import boot_session
        old_user = frappe.session.user
        frappe.set_user(_USERS["u1"])
        try:
            frappe.cache.delete_value(f"caps:user:{_USERS['u1']}")
            bootinfo = frappe._dict()
            boot_session(bootinfo)
            self.assertIn("caps", bootinfo)
        finally:
            frappe.set_user(old_user)

    def test_boot_contains_capabilities(self):
        """bootinfo.caps should contain user's capabilities."""
        from caps.boot import boot_session
        old_user = frappe.session.user
        frappe.set_user(_USERS["u1"])
        try:
            frappe.cache.delete_value(f"caps:user:{_USERS['u1']}")
            bootinfo = frappe._dict()
            boot_session(bootinfo)
            self.assertIn(f"{_TEST_PREFIX}cap:one",
                          bootinfo["caps"]["capabilities"])
        finally:
            frappe.set_user(old_user)

    def test_boot_contains_field_restrictions(self):
        """bootinfo.caps should have field_restrictions dict."""
        from caps.boot import boot_session
        old_user = frappe.session.user
        frappe.set_user(_USERS["u1"])
        try:
            frappe.cache.delete_value(f"caps:user:{_USERS['u1']}")
            bootinfo = frappe._dict()
            boot_session(bootinfo)
            self.assertIn("field_restrictions", bootinfo["caps"])
            self.assertIsInstance(bootinfo["caps"]["field_restrictions"], dict)
        finally:
            frappe.set_user(old_user)

    def test_boot_contains_action_restrictions(self):
        """bootinfo.caps should have action_restrictions dict."""
        from caps.boot import boot_session
        old_user = frappe.session.user
        frappe.set_user(_USERS["u1"])
        try:
            frappe.cache.delete_value(f"caps:user:{_USERS['u1']}")
            bootinfo = frappe._dict()
            boot_session(bootinfo)
            self.assertIn("action_restrictions", bootinfo["caps"])
        finally:
            frappe.set_user(old_user)

    def test_boot_contains_version(self):
        """bootinfo.caps should have a version integer."""
        from caps.boot import boot_session
        old_user = frappe.session.user
        frappe.set_user(_USERS["u1"])
        try:
            bootinfo = frappe._dict()
            boot_session(bootinfo)
            self.assertIn("version", bootinfo["caps"])
            self.assertIsInstance(bootinfo["caps"]["version"], int)
        finally:
            frappe.set_user(old_user)

    def test_boot_guest_skipped(self):
        """boot_session should skip for Guest users."""
        from caps.boot import boot_session
        old_user = frappe.session.user
        frappe.set_user("Guest")
        try:
            bootinfo = frappe._dict()
            boot_session(bootinfo)
            self.assertNotIn("caps", bootinfo)
        finally:
            frappe.set_user(old_user)

    def test_boot_never_raises(self):
        """boot_session should never raise, even with errors."""
        from caps.boot import boot_session
        old_user = frappe.session.user
        frappe.set_user(_USERS["u1"])
        try:
            bootinfo = frappe._dict()
            # Even if something goes wrong internally, boot should succeed
            boot_session(bootinfo)
            self.assertIn("caps", bootinfo)
        finally:
            frappe.set_user(old_user)


# ── Capability Controller Tests ──────────────────────────────────────


class TestCapabilityController(unittest.TestCase):
    """Tests for Capability DocType controller."""

    def test_autoname_from_name1(self):
        """Capability should auto-name from name1 field."""
        cap = frappe.get_doc({
            "doctype": "Capability",
            "name1": f"{_TEST_PREFIX}autoname:test",
            "label": "test",
            "category": "Custom",
            "is_active": 1,
        })
        cap.insert(ignore_permissions=True)
        self.assertEqual(cap.name, f"{_TEST_PREFIX}autoname:test")
        cap.delete(force=True, ignore_permissions=True)

    def test_validate_name_format_rejects_single_part(self):
        """Capability name without colon should be rejected."""
        cap = frappe.get_doc({
            "doctype": "Capability",
            "name1": f"{_TEST_PREFIX}badname",
            "label": "bad",
            "category": "Custom",
            "is_active": 1,
        })
        with self.assertRaises(frappe.ValidationError):
            cap.insert(ignore_permissions=True)

    def test_validate_name_format_accepts_colon(self):
        """Capability name with colon should be accepted."""
        cap = frappe.get_doc({
            "doctype": "Capability",
            "name1": f"{_TEST_PREFIX}ok:name",
            "label": "ok",
            "category": "Custom",
            "is_active": 1,
        })
        cap.insert(ignore_permissions=True)
        cap.delete(force=True, ignore_permissions=True)


# ── Capability Bundle Controller Tests ────────────────────────────────


class TestBundleController(unittest.TestCase):
    """Tests for Capability Bundle controller — duplicate detection."""

    @classmethod
    def setUpClass(cls):
        _setup_bc_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_bc_data()

    def test_duplicate_capability_rejected(self):
        """Bundle with duplicate capabilities should be rejected."""
        bundle = frappe.get_doc({
            "doctype": "Capability Bundle",
            "__newname": f"{_TEST_PREFIX}dup_bundle",
            "label": f"{_TEST_PREFIX}dup_bundle",
            "capabilities": [
                {"capability": f"{_TEST_PREFIX}cap:one"},
                {"capability": f"{_TEST_PREFIX}cap:one"},  # duplicate
            ],
        })
        with self.assertRaises(frappe.ValidationError):
            bundle.insert(ignore_permissions=True)

    def test_unique_capabilities_accepted(self):
        """Bundle with unique capabilities should be accepted."""
        bundle = frappe.get_doc({
            "doctype": "Capability Bundle",
            "__newname": f"{_TEST_PREFIX}ok_bundle",
            "label": f"{_TEST_PREFIX}ok_bundle",
            "capabilities": [
                {"capability": f"{_TEST_PREFIX}cap:one"},
                {"capability": f"{_TEST_PREFIX}cap:two"},
            ],
        })
        bundle.insert(ignore_permissions=True)
        bundle.delete(force=True, ignore_permissions=True)


# ── Permission Group Controller Tests ─────────────────────────────────


class TestPermissionGroupController(unittest.TestCase):
    """Tests for Permission Group controller."""

    @classmethod
    def setUpClass(cls):
        _setup_bc_data()

    @classmethod
    def tearDownClass(cls):
        # Clean any leftover groups
        for name in frappe.get_all("Permission Group",
                                    filters={"label": ("like", f"{_TEST_PREFIX}%")},
                                    pluck="name"):
            frappe.delete_doc("Permission Group", name,
                              force=True, ignore_permissions=True)
        frappe.db.commit()
        _teardown_bc_data()

    def test_member_timestamp_auto_set(self):
        """New members should get added_on and added_by stamped."""
        grp = frappe.get_doc({
            "doctype": "Permission Group",
            "__newname": f"{_TEST_PREFIX}stamp_grp",
            "label": f"{_TEST_PREFIX}stamp_grp",
            "group_type": "Manual",
            "members": [{"user": _USERS["u1"]}],
        })
        grp.insert(ignore_permissions=True)
        self.assertIsNotNone(grp.members[0].added_on)
        self.assertIsNotNone(grp.members[0].added_by)
        grp.delete(force=True, ignore_permissions=True)

    def test_circular_parent_rejected(self):
        """Circular parent_group references should be rejected."""
        # Create two groups
        g1 = frappe.get_doc({
            "doctype": "Permission Group",
            "__newname": f"{_TEST_PREFIX}circ_g1",
            "label": f"{_TEST_PREFIX}circ_g1",
            "group_type": "Manual",
        })
        g1.insert(ignore_permissions=True)

        g2 = frappe.get_doc({
            "doctype": "Permission Group",
            "__newname": f"{_TEST_PREFIX}circ_g2",
            "label": f"{_TEST_PREFIX}circ_g2",
            "group_type": "Manual",
            "parent_group": f"{_TEST_PREFIX}circ_g1",
        })
        g2.insert(ignore_permissions=True)

        # Now try to set g1's parent to g2 → circular
        g1.parent_group = f"{_TEST_PREFIX}circ_g2"
        with self.assertRaises(frappe.ValidationError):
            g1.save(ignore_permissions=True)

        # Cleanup
        g2.delete(force=True, ignore_permissions=True)
        g1.delete(force=True, ignore_permissions=True)


# ── Field Capability Map Controller Tests ─────────────────────────────


class TestFieldCapabilityMapController(unittest.TestCase):
    """Tests for Field Capability Map controller."""

    @classmethod
    def setUpClass(cls):
        _setup_bc_data()

    @classmethod
    def tearDownClass(cls):
        for name in frappe.get_all("Field Capability Map",
                                    filters={"capability": ("like", f"{_TEST_PREFIX}%")},
                                    pluck="name"):
            frappe.delete_doc("Field Capability Map", name,
                              force=True, ignore_permissions=True)
        frappe.db.commit()
        _teardown_bc_data()

    def test_auto_fetch_field_label(self):
        """Field label should be auto-fetched from the target DocType meta."""
        fm = frappe.get_doc({
            "doctype": "Field Capability Map",
            "doctype_name": "Note",
            "fieldname": "title",
            "capability": f"{_TEST_PREFIX}cap:one",
            "behavior": "hide",
            "priority": 1,
        })
        fm.insert(ignore_permissions=True)
        self.assertIsNotNone(fm.field_label)
        fm.delete(force=True, ignore_permissions=True)

    def test_invalid_fieldname_rejected(self):
        """Non-existent field should be rejected."""
        fm = frappe.get_doc({
            "doctype": "Field Capability Map",
            "doctype_name": "Note",
            "fieldname": "totally_fake_field_xyz",
            "capability": f"{_TEST_PREFIX}cap:one",
            "behavior": "hide",
            "priority": 1,
        })
        with self.assertRaises(frappe.ValidationError):
            fm.insert(ignore_permissions=True)


# ── User Capability Controller Tests ──────────────────────────────────


class TestUserCapabilityController(unittest.TestCase):
    """Tests for User Capability controller."""

    @classmethod
    def setUpClass(cls):
        _setup_bc_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_bc_data()

    def test_autoname_from_user(self):
        """User Capability should auto-name from user field."""
        uc = frappe.get_doc("User Capability", _USERS["u1"])
        self.assertEqual(uc.name, _USERS["u1"])

    def test_grants_auto_stamped(self):
        """New grants should get granted_on and granted_by stamped."""
        uc = frappe.get_doc("User Capability", _USERS["u1"])
        for row in uc.direct_capabilities:
            self.assertIsNotNone(row.granted_on)
            self.assertIsNotNone(row.granted_by)


# ── Role Capability Map Controller Tests ──────────────────────────────


class TestRoleCapabilityMapController(unittest.TestCase):
    """Tests for Role Capability Map controller."""

    def test_autoname_from_role(self):
        """Role Capability Map should auto-name from role field."""
        role_name = f"{_TEST_PREFIX}autoname_role"
        if not frappe.db.exists("Role", role_name):
            frappe.get_doc({
                "doctype": "Role",
                "role_name": role_name,
                "desk_access": 1,
            }).insert(ignore_permissions=True)

        # Create a minimal cap for the map
        cap_name = f"{_TEST_PREFIX}cap:autoname"
        if not frappe.db.exists("Capability", cap_name):
            frappe.get_doc({
                "doctype": "Capability",
                "name1": cap_name,
                "label": cap_name,
                "category": "Custom",
                "is_active": 1,
            }).insert(ignore_permissions=True)

        rcm = frappe.get_doc({
            "doctype": "Role Capability Map",
            "role": role_name,
            "role_capabilities": [{"capability": cap_name}],
        })
        rcm.insert(ignore_permissions=True)
        self.assertEqual(rcm.name, role_name)

        # Cleanup
        rcm.delete(force=True, ignore_permissions=True)
        if frappe.db.exists("Capability", cap_name):
            frappe.delete_doc("Capability", cap_name,
                              force=True, ignore_permissions=True)
        if frappe.db.exists("Role", role_name):
            frappe.delete_doc("Role", role_name,
                              force=True, ignore_permissions=True)


# ── Install Hook Tests ────────────────────────────────────────────────


class TestInstall(unittest.TestCase):
    """Tests for caps.install hooks."""

    def test_caps_admin_role_exists(self):
        """CAPS Admin role should exist."""
        self.assertTrue(frappe.db.exists("Role", "CAPS Admin"))

    def test_caps_manager_role_exists(self):
        """CAPS Manager role should exist."""
        self.assertTrue(frappe.db.exists("Role", "CAPS Manager"))
