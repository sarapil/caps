"""
CAPS — Test Configuration
Shared pytest fixtures for CAPS.
"""

import frappe
import pytest


@pytest.fixture(scope="session")
def site():
    """Return the test site name."""
    return frappe.local.site


@pytest.fixture(autouse=True)
def reset_flags():
    """Reset frappe flags between tests."""
    yield
    frappe.flags.pop("in_test", None)


@pytest.fixture()
def admin_user():
    """Login as Administrator for permission tests."""
    frappe.set_user("Administrator")
    yield "Administrator"
    frappe.set_user("Administrator")
