# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS — Multi-Tenancy Tests (Phase 28)
=======================================

Tests for site profile management and cross-site comparison.

Prefix: capstest_tenancy_

Run with:
    bench --site dev.localhost run-tests --app caps \
        --module caps.tests.test_tenancy
"""

import json
import frappe
import unittest

_PREFIX = "capstest_tenancy_"

_PROFILES = {
    "site_a": f"{_PREFIX}site_a",
    "site_b": f"{_PREFIX}site_b",
}


def _setup_data():
    _teardown_data()

    # Create two site profiles with different configs
    config_a = {
        "capabilities": [
            {"name": "cap_1"},
            {"name": "cap_2"},
            {"name": "cap_3"},
        ],
        "bundles": [{"name": "bundle_1"}],
        "field_maps": [
            {"doctype_name": "User", "fieldname": "phone", "capability": "cap_1"},
        ],
        "action_maps": [],
        "policies": [],
        "role_maps": [],
        "groups": [],
    }

    config_b = {
        "capabilities": [
            {"name": "cap_2"},
            {"name": "cap_3"},
            {"name": "cap_4"},
        ],
        "bundles": [{"name": "bundle_1"}, {"name": "bundle_2"}],
        "field_maps": [],
        "action_maps": [],
        "policies": [],
        "role_maps": [],
        "groups": [],
    }

    frappe.get_doc({
        "doctype": "CAPS Site Profile",
        "site_name": _PROFILES["site_a"],
        "site_label": "Site A",
        "is_active": 1,
        "config_json": json.dumps(config_a),
    }).insert(ignore_permissions=True)

    frappe.get_doc({
        "doctype": "CAPS Site Profile",
        "site_name": _PROFILES["site_b"],
        "site_label": "Site B",
        "is_active": 1,
        "config_json": json.dumps(config_b),
    }).insert(ignore_permissions=True)

    frappe.db.commit()


def _teardown_data():
    for name in _PROFILES.values():
        if frappe.db.exists("CAPS Site Profile", name):
            frappe.delete_doc("CAPS Site Profile", name, force=True, ignore_permissions=True)
    frappe.db.commit()


class TestSiteProfileCreation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _setup_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_data()

    def test_profiles_exist(self):
        """Both test profiles should exist."""
        self.assertTrue(frappe.db.exists("CAPS Site Profile", _PROFILES["site_a"]))
        self.assertTrue(frappe.db.exists("CAPS Site Profile", _PROFILES["site_b"]))

    def test_profile_config_json(self):
        """Profile config JSON should be valid."""
        doc = frappe.get_doc("CAPS Site Profile", _PROFILES["site_a"])
        config = json.loads(doc.config_json)
        self.assertEqual(len(config["capabilities"]), 3)
        self.assertEqual(len(config["bundles"]), 1)

    def test_url_validation(self):
        """Site URL must start with http:// or https://."""
        with self.assertRaises(frappe.ValidationError):
            doc = frappe.get_doc("CAPS Site Profile", _PROFILES["site_a"])
            doc.site_url = "ftp://invalid"
            doc.save()


class TestSiteProfileComparison(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _setup_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_data()

    def test_compare_capabilities(self):
        """Compare should show correct only_in_a, only_in_b, common."""
        from caps.api_tenancy import compare_site_profiles
        result = compare_site_profiles(_PROFILES["site_a"], _PROFILES["site_b"])

        caps_diff = result["capabilities"]
        self.assertIn("cap_1", caps_diff["only_in_a"])
        self.assertIn("cap_4", caps_diff["only_in_b"])
        self.assertIn("cap_2", caps_diff["common"])
        self.assertIn("cap_3", caps_diff["common"])

    def test_compare_bundles(self):
        """Bundle comparison should detect differences."""
        from caps.api_tenancy import compare_site_profiles
        result = compare_site_profiles(_PROFILES["site_a"], _PROFILES["site_b"])

        bundle_diff = result["bundles"]
        self.assertIn("bundle_2", bundle_diff["only_in_b"])
        self.assertIn("bundle_1", bundle_diff["common"])

    def test_compare_summaries(self):
        """Both sides should have correct summary counts."""
        from caps.api_tenancy import compare_site_profiles
        result = compare_site_profiles(_PROFILES["site_a"], _PROFILES["site_b"])

        self.assertEqual(result["summary_a"]["capabilities"], 3)
        self.assertEqual(result["summary_b"]["capabilities"], 3)
        self.assertEqual(result["summary_a"]["bundles"], 1)
        self.assertEqual(result["summary_b"]["bundles"], 2)

    def test_compare_field_maps(self):
        """Field map diff should show counts."""
        from caps.api_tenancy import compare_site_profiles
        result = compare_site_profiles(_PROFILES["site_a"], _PROFILES["site_b"])

        fm_diff = result["field_maps"]
        self.assertEqual(fm_diff["only_in_a"], 1)
        self.assertEqual(fm_diff["only_in_b"], 0)


class TestSiteProfileSnapshot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _teardown_data()

    @classmethod
    def tearDownClass(cls):
        _teardown_data()

    def test_snapshot_creates_profile(self):
        """snapshot_site_config should create a new profile."""
        from caps.api_tenancy import snapshot_site_config
        result = snapshot_site_config(profile_name=_PROFILES["site_a"])

        self.assertEqual(result["profile"], _PROFILES["site_a"])
        self.assertIn("summary", result)
        self.assertTrue(frappe.db.exists("CAPS Site Profile", _PROFILES["site_a"]))

    def test_snapshot_updates_existing(self):
        """Calling snapshot again should update, not duplicate."""
        from caps.api_tenancy import snapshot_site_config
        snapshot_site_config(profile_name=_PROFILES["site_a"])
        result = snapshot_site_config(profile_name=_PROFILES["site_a"])

        self.assertIsNotNone(result["last_sync"])

    def test_get_site_profiles_list(self):
        """get_site_profiles should return profiles with summaries."""
        from caps.api_tenancy import snapshot_site_config, get_site_profiles
        snapshot_site_config(profile_name=_PROFILES["site_a"])

        profiles = get_site_profiles()
        names = [p["name"] for p in profiles]
        self.assertIn(_PROFILES["site_a"], names)

    def test_get_profile_detail(self):
        """get_profile_detail should return detailed info."""
        from caps.api_tenancy import snapshot_site_config, get_profile_detail
        snapshot_site_config(profile_name=_PROFILES["site_a"])

        detail = get_profile_detail(_PROFILES["site_a"])
        self.assertIn("summary", detail)
        self.assertIsInstance(detail["capabilities"], list)
