# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS — Test Configuration
Shared fixtures and helpers for CAPS tests.
"""

import frappe
import pytest


@pytest.fixture(scope="module")
def site_setup():
    """Ensure test site is set up correctly."""
    frappe.set_user("Administrator")
    yield
    frappe.set_user("Administrator")


@pytest.fixture
def as_admin():
    """Run test as Administrator."""
    frappe.set_user("Administrator")
    yield
    frappe.set_user("Administrator")


@pytest.fixture
def as_guest():
    """Run test as Guest user."""
    frappe.set_user("Guest")
    yield
    frappe.set_user("Administrator")


@pytest.fixture
def test_user():
    """Create and return a temporary test user."""
    user_email = "test_caps@example.com"
    if not frappe.db.exists("User", user_email):
        user = frappe.get_doc({
            "doctype": "User",
            "email": user_email,
            "first_name": "Test",
            "last_name": "CAPS",
            "enabled": 1,
            "user_type": "System User",
        })
        user.insert(ignore_permissions=True)
        frappe.db.commit()

    frappe.set_user(user_email)
    yield user_email
    frappe.set_user("Administrator")
    if frappe.db.exists("User", user_email):
        frappe.delete_doc("User", user_email, force=True)
        frappe.db.commit()
