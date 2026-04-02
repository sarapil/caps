"""
CAPS — Permission Tests
Role-based access control and CAPS capability tests.
"""

import frappe
from frappe.tests import IntegrationTestCase


class TestCAPSPermissions(IntegrationTestCase):
    """Permission and CAPS capability tests for CAPS."""

    def test_guest_cannot_access(self):
        """Guest users cannot access protected endpoints."""
        pass  # TODO: Implement
