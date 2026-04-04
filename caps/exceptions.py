# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS — Custom Exception Hierarchy
Capability-Based Access Control
"""

import frappe


class CAPSError(Exception):
    """CAPS base exception — all app-specific errors inherit from this."""

    def __init__(self, message=None, title=None):
        self.message = message or frappe._("An error occurred in CAPS")
        self.title = title or frappe._("CAPS Error")
        super().__init__(self.message)


class ValidationError(CAPSError):
    """Raised when input validation fails."""

    def __init__(self, message=None, field=None):
        self.field = field
        super().__init__(
            message or frappe._("Validation failed"),
            title=frappe._("Validation Error"),
        )


class NotFoundError(CAPSError):
    """Raised when a requested resource is not found."""

    def __init__(self, doctype=None, name=None):
        msg = frappe._("{0} {1} not found").format(doctype or "Record", name or "")
        super().__init__(msg, title=frappe._("Not Found"))


class PermissionError(CAPSError):
    """Raised when user lacks required permissions or CAPS capabilities."""

    def __init__(self, action=None, doctype=None):
        msg = frappe._("You do not have permission to {0} {1}").format(
            action or "access", doctype or "this resource"
        )
        super().__init__(msg, title=frappe._("Permission Denied"))


class ConfigurationError(CAPSError):
    """Raised when app configuration is incomplete or invalid."""

    def __init__(self, setting=None):
        msg = frappe._("{0} is not configured properly. Please check Settings.").format(
            setting or meta['title']
        )
        super().__init__(msg, title=frappe._("Configuration Error"))


class IntegrationError(CAPSError):
    """Raised when an external integration fails (API call, webhook, etc.)."""

    def __init__(self, service=None, message=None):
        msg = frappe._("Integration error with {0}: {1}").format(
            service or "external service", message or "unknown error"
        )
        super().__init__(msg, title=frappe._("Integration Error"))


class RateLimitError(CAPSError):
    """Raised when rate limit is exceeded."""

    def __init__(self):
        super().__init__(
            frappe._("Too many requests. Please try again later."),
            title=frappe._("Rate Limit Exceeded"),
        )
