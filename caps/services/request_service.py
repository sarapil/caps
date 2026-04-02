"""
CAPS — RequestService
Business logic for request service operations.
"""

import frappe
from frappe import _


class RequestService:
    """Service class for request service business logic.

    Separates business rules from API endpoint handling and direct
    DocType manipulation. API endpoints should delegate to this class.
    """

    @staticmethod
    def get_list(filters=None, page=1, page_size=20):
        """Get paginated list of records."""
        raise NotImplementedError("Implement in subclass or override")

    @staticmethod
    def get_detail(name):
        """Get single record details."""
        raise NotImplementedError("Implement in subclass or override")

    @staticmethod
    def create(data):
        """Create a new record with validation."""
        raise NotImplementedError("Implement in subclass or override")

    @staticmethod
    def update(name, data):
        """Update an existing record."""
        raise NotImplementedError("Implement in subclass or override")

    @staticmethod
    def validate(data):
        """Validate data before create/update."""
        raise NotImplementedError("Implement in subclass or override")
