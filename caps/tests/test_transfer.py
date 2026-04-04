# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS — Import / Export Tests
==============================

Tests for api_transfer.py:
 - export_config
 - import_config (merge + overwrite)
 - validate_import
 - round-trip fidelity

Prefix: capstest_xfr_

Run with:
    bench --site dev.localhost run-tests --app caps \
        --module caps.tests.test_transfer
"""

import json
import frappe
import unittest

_TEST_PREFIX = "capstest_xfr_"

_CAPS = {
    "alpha": f"{_TEST_PREFIX}cap:alpha",
    "beta": f"{_TEST_PREFIX}cap:beta",
    "gamma": f"{_TEST_PREFIX}cap:gamma",
}

_BUNDLE = f"{_TEST_PREFIX}bundle:basic"


def _setup_transfer_data():
    _teardown_transfer_data()

    # Create capabilities
    for key, name in _CAPS.items():
        frappe.get_doc({
            "doctype": "Capability",
            "name1": name,
            "label": f"Transfer {key}",
            "category": "Custom",
            "is_active": 1,
            "is_delegatable": 0,
        }).insert(ignore_permissions=True)

    # Add a prerequisite to alpha -> beta
    doc = frappe.get_doc("Capability", _CAPS["alpha"])
    doc.append("prerequisites", {
        "prerequisite": _CAPS["beta"],
        "is_hard": 1,
    })
    doc.save(ignore_permissions=True)

    # Create a bundle
    frappe.get_doc({
        "doctype": "Capability Bundle",
        "__newname": _BUNDLE,
        "label": "Test bundle",
        "description": "Test bundle",
        "capabilities": [
            {"capability": _CAPS["alpha"]},
            {"capability": _CAPS["beta"]},
        ],
    }).insert(ignore_permissions=True)

    frappe.db.commit()


def _teardown_transfer_data():
    # Clean audit logs
    frappe.db.sql(
        "DELETE FROM `tabCAPS Audit Log` WHERE capability LIKE %s",
        (f"{_TEST_PREFIX}%",),
    )

    # Clean bundles
    for name in frappe.get_all(
        "Capability Bundle",
        filters={"name": ("like", f"{_TEST_PREFIX}%")},
        pluck="name",
    ):
        frappe.delete_doc("Capability Bundle", name, force=True, ignore_permissions=True)

    # Clean role maps
    for name in frappe.get_all(
        "Role Capability Map",
        filters={"role": ("like", f"{_TEST_PREFIX}%")},
        pluck="name",
    ):
        frappe.delete_doc("Role Capability Map", name, force=True, ignore_permissions=True)

    # Clean field maps
    for name in frappe.get_all(
        "Field Capability Map",
        filters={"capability": ("like", f"{_TEST_PREFIX}%")},
        pluck="name",
    ):
        frappe.delete_doc("Field Capability Map", name, force=True, ignore_permissions=True)

    # Clean action maps
    for name in frappe.get_all(
        "Action Capability Map",
        filters={"capability": ("like", f"{_TEST_PREFIX}%")},
        pluck="name",
    ):
        frappe.delete_doc("Action Capability Map", name, force=True, ignore_permissions=True)

    # Clean policies
    for name in frappe.get_all(
        "Capability Policy",
        filters={"policy_name": ("like", f"{_TEST_PREFIX}%")},
        pluck="name",
    ):
        frappe.delete_doc("Capability Policy", name, force=True, ignore_permissions=True)

    # Clean capabilities
    for cap_name in _CAPS.values():
        if frappe.db.exists("Capability", cap_name):
            frappe.delete_doc("Capability", cap_name, force=True, ignore_permissions=True)

    # Clean any imported capabilities from round-trip tests
    for name in frappe.get_all(
        "Capability",
        filters={"name1": ("like", f"{_TEST_PREFIX}%")},
        pluck="name",
    ):
        frappe.delete_doc("Capability", name, force=True, ignore_permissions=True)

    frappe.db.commit()


class TestTransfer(unittest.TestCase):
    """Test CAPS Import/Export functionality."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        _setup_transfer_data()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        _teardown_transfer_data()

    # ─── Export Tests ──────────────────────────────────────────────

    def test_export_config_returns_package(self):
        """Export should return a well-formed package with version and metadata."""
        from caps.api_transfer import export_config
        pkg = export_config()
        self.assertIn("caps_export_version", pkg)
        self.assertIn("exported_at", pkg)
        self.assertIn("exported_by", pkg)
        self.assertEqual(pkg["caps_export_version"], 1)

    def test_export_includes_capabilities(self):
        """Export should include capabilities with correct fields."""
        from caps.api_transfer import export_config
        pkg = export_config()
        caps = pkg.get("capabilities", [])
        names = [c["name1"] for c in caps if c.get("name1", "").startswith(_TEST_PREFIX)]
        for cap_name in _CAPS.values():
            self.assertIn(cap_name, names)

    def test_export_includes_prerequisites(self):
        """Exported capabilities should include their prerequisites."""
        from caps.api_transfer import export_config
        pkg = export_config()
        alpha = next(
            (c for c in pkg.get("capabilities", []) if c.get("name1") == _CAPS["alpha"]),
            None,
        )
        self.assertIsNotNone(alpha)
        prereqs = alpha.get("prerequisites", [])
        self.assertTrue(len(prereqs) >= 1)
        prereq_names = [p["prerequisite"] for p in prereqs]
        self.assertIn(_CAPS["beta"], prereq_names)

    def test_export_includes_bundles(self):
        """Export should include bundles with their items."""
        from caps.api_transfer import export_config
        pkg = export_config()
        bundles = pkg.get("bundles", [])
        our_bundle = next(
            (b for b in bundles if b.get("name") == _BUNDLE),
            None,
        )
        self.assertIsNotNone(our_bundle, f"Bundle {_BUNDLE} not found in export")
        self.assertTrue(len(our_bundle.get("items", [])) >= 2)

    def test_export_selective_flags(self):
        """Export with flags off should omit those sections."""
        from caps.api_transfer import export_config
        pkg = export_config(
            include_capabilities=True,
            include_bundles=False,
            include_role_maps=False,
            include_field_maps=False,
            include_action_maps=False,
            include_policies=False,
            include_groups=False,
        )
        self.assertIn("capabilities", pkg)
        self.assertNotIn("bundles", pkg)
        self.assertNotIn("role_maps", pkg)

    # ─── Import Tests ─────────────────────────────────────────────

    def test_import_merge_skips_existing(self):
        """Import in merge mode should skip existing capabilities."""
        from caps.api_transfer import export_config, import_config
        pkg = export_config()

        # Import same data in merge mode
        result = import_config(json.dumps(pkg), mode="merge")
        # Our test caps already exist, so they should be skipped
        self.assertGreaterEqual(result["skipped"], len(_CAPS))
        self.assertEqual(len(result["errors"]), 0)

    def test_import_overwrite_updates(self):
        """Import in overwrite mode should update existing capabilities."""
        from caps.api_transfer import export_config, import_config
        pkg = export_config()

        # Modify a capability label in the export
        for c in pkg.get("capabilities", []):
            if c.get("name1") == _CAPS["alpha"]:
                c["label"] = "Updated Alpha Label"

        result = import_config(pkg, mode="overwrite")
        self.assertGreater(result["updated"], 0)
        self.assertEqual(len(result["errors"]), 0)

        # Verify the label was updated
        doc = frappe.get_doc("Capability", _CAPS["alpha"])
        self.assertEqual(doc.label, "Updated Alpha Label")

    def test_import_creates_new(self):
        """Import should create new capabilities that don't exist."""
        from caps.api_transfer import import_config

        new_cap_name = f"{_TEST_PREFIX}cap:imported_new"
        pkg = {
            "caps_export_version": 1,
            "capabilities": [{
                "name1": new_cap_name,
                "label": "Imported New",
                "category": "Custom",
                "is_active": 1,
                "prerequisites": [],
            }],
        }
        result = import_config(pkg, mode="merge")
        self.assertEqual(result["created"], 1)
        self.assertTrue(frappe.db.exists("Capability", new_cap_name))

        # Cleanup
        frappe.delete_doc("Capability", new_cap_name, force=True, ignore_permissions=True)
        frappe.db.commit()

    def test_import_invalid_mode_throws(self):
        """Import with invalid mode should throw."""
        from caps.api_transfer import import_config
        with self.assertRaises(Exception):
            import_config("{}", mode="invalid")

    def test_import_future_version_throws(self):
        """Import with a future version should throw."""
        from caps.api_transfer import import_config
        pkg = {"caps_export_version": 999}
        with self.assertRaises(Exception):
            import_config(json.dumps(pkg))

    # ─── Validate Import Tests ────────────────────────────────────

    def test_validate_import(self):
        """validate_import should report what would happen without changes."""
        from caps.api_transfer import export_config, validate_import
        pkg = export_config()
        report = validate_import(json.dumps(pkg))
        self.assertTrue(report["version_ok"])
        self.assertIn("capabilities", report["sections"])
        caps_section = report["sections"]["capabilities"]
        self.assertGreaterEqual(caps_section["existing"], len(_CAPS))

    # ─── Round-Trip Test ──────────────────────────────────────────

    def test_round_trip_fidelity(self):
        """Export → import → export should be stable."""
        from caps.api_transfer import export_config, import_config

        pkg1 = export_config()

        # Count test caps in first export
        test_caps_1 = [c for c in pkg1.get("capabilities", [])
                       if c.get("name1", "").startswith(_TEST_PREFIX)]

        # Import in merge (should be all skips)
        result = import_config(json.dumps(pkg1), mode="merge")
        self.assertEqual(len(result["errors"]), 0)

        pkg2 = export_config()
        test_caps_2 = [c for c in pkg2.get("capabilities", [])
                       if c.get("name1", "").startswith(_TEST_PREFIX)]

        # Same test capabilities count
        self.assertEqual(len(test_caps_1), len(test_caps_2))

    def test_import_string_and_dict(self):
        """import_config should accept both JSON string and dict."""
        from caps.api_transfer import import_config

        pkg = {"caps_export_version": 1, "capabilities": []}

        # Dict input
        r1 = import_config(pkg, mode="merge")
        self.assertEqual(len(r1["errors"]), 0)

        # String input
        r2 = import_config(json.dumps(pkg), mode="merge")
        self.assertEqual(len(r2["errors"]), 0)
