"""
CAPS — Integration Hub Tests (Phase 31)
=========================================

Tests for integration pack discovery, preview, install, and uninstall.

Prefix: capstest_integ_

Run with:
    bench --site dev.localhost run-tests --app caps \
        --module caps.tests.test_integrations
"""

import frappe
import unittest
import json


class TestIntegrationPackDocType(unittest.TestCase):
    """Tests for the CAPS Integration Pack DocType."""

    _PREFIX = "capstest_integ_"

    def tearDown(self):
        for name in frappe.get_all(
            "CAPS Integration Pack",
            filters={"pack_name": ("like", f"{self._PREFIX}%")},
            pluck="name",
        ):
            frappe.delete_doc("CAPS Integration Pack", name, force=True, ignore_permissions=True)
        frappe.db.commit()

    def test_create_custom_pack(self):
        """Should create a custom integration pack."""
        doc = frappe.get_doc({
            "doctype": "CAPS Integration Pack",
            "pack_name": f"{self._PREFIX}testpack",
            "pack_label": "Test Pack",
            "app": "caps",
            "version": "1.0",
            "config_json": json.dumps({"capabilities": []}),
        }).insert(ignore_permissions=True)
        frappe.db.commit()

        self.assertTrue(frappe.db.exists("CAPS Integration Pack", doc.name))

    def test_invalid_json(self):
        """Should reject invalid JSON in config_json."""
        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc({
                "doctype": "CAPS Integration Pack",
                "pack_name": f"{self._PREFIX}badjson",
                "pack_label": "Bad JSON",
                "config_json": "{ not valid json }",
            }).insert(ignore_permissions=True)


class TestBuiltinPacks(unittest.TestCase):
    """Tests for built-in integration pack discovery and preview."""

    def test_get_available_packs(self):
        """Should list built-in packs."""
        from caps.api_integrations import get_available_packs
        packs = get_available_packs()

        names = [p["pack_name"] for p in packs]
        self.assertIn("erpnext_core", names)
        self.assertIn("hrms_core", names)
        self.assertIn("common_data_protection", names)

    def test_preview_erpnext_core(self):
        """Preview should show capabilities and bundles."""
        from caps.api_integrations import preview_pack
        preview = preview_pack("erpnext_core")

        self.assertIn("capabilities", preview)
        self.assertIn("bundles", preview)
        self.assertTrue(len(preview["capabilities"]) > 0)

    def test_preview_invalid_pack(self):
        """Preview of non-existent pack should raise."""
        from caps.api_integrations import preview_pack
        with self.assertRaises(frappe.ValidationError):
            preview_pack("nonexistent_pack_12345")


class TestPackInstallUninstall(unittest.TestCase):
    """Tests for installing and uninstalling integration packs."""

    _PACK = "common_data_protection"

    def setUp(self):
        self._cleanup_pack()

    def tearDown(self):
        self._cleanup_pack()

    def _cleanup_pack(self):
        """Remove all items created by the pack."""
        from caps.api_integrations import _BUILTIN_PACKS

        pack = _BUILTIN_PACKS.get(self._PACK, {})
        config = pack.get("config", {})

        # Remove bundles first (they reference capabilities)
        for b in config.get("bundles", []):
            bname = b["name"]
            if frappe.db.exists("Capability Bundle", bname):
                frappe.delete_doc("Capability Bundle", bname, force=True, ignore_permissions=True)

        # Remove capabilities
        for c in config.get("capabilities", []):
            cname = c["name1"]
            if frappe.db.exists("Capability", cname):
                frappe.delete_doc("Capability", cname, force=True, ignore_permissions=True)

        # Remove field maps
        for fm in config.get("field_maps", []):
            for fmd in frappe.get_all(
                "Field Capability Map",
                filters={"capability": fm["capability"], "doctype_name": fm["doctype_name"]},
                pluck="name",
            ):
                frappe.delete_doc("Field Capability Map", fmd, force=True, ignore_permissions=True)

        frappe.db.commit()

    def test_install_creates_capabilities(self):
        """install_pack should create capabilities."""
        from caps.api_integrations import install_pack, _BUILTIN_PACKS

        result = install_pack(self._PACK)
        self.assertIn("created", result)

        config = _BUILTIN_PACKS[self._PACK]["config"]
        for c in config["capabilities"]:
            self.assertTrue(
                frappe.db.exists("Capability", c["name1"]),
                f"Capability {c['name1']} should exist after install",
            )

    def test_install_idempotent(self):
        """Installing same pack twice should not raise."""
        from caps.api_integrations import install_pack

        install_pack(self._PACK)
        result = install_pack(self._PACK)  # Second install

        # Should report skipped items
        self.assertIn("skipped", result)
        self.assertTrue(result["skipped"] > 0)

    def test_uninstall_removes_items(self):
        """uninstall_pack should remove capabilities and bundles."""
        from caps.api_integrations import install_pack, uninstall_pack, _BUILTIN_PACKS

        install_pack(self._PACK)

        result = uninstall_pack(self._PACK)
        self.assertIn("removed", result)

        config = _BUILTIN_PACKS[self._PACK]["config"]
        for c in config["capabilities"]:
            self.assertFalse(
                frappe.db.exists("Capability", c["name1"]),
                f"Capability {c['name1']} should not exist after uninstall",
            )

    def test_install_creates_bundles(self):
        """install_pack should create bundles with items."""
        from caps.api_integrations import install_pack, _BUILTIN_PACKS

        install_pack(self._PACK)

        config = _BUILTIN_PACKS[self._PACK]["config"]
        for b in config.get("bundles", []):
            self.assertTrue(
                frappe.db.exists("Capability Bundle", b["name"]),
                f"Bundle {b['name']} should exist after install",
            )
