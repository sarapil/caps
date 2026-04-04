# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS — CAPS Gate
Capability gating utilities for CAPS ↔ CAPS integration.
"""

import frappe
from frappe import _
from functools import wraps


class CapabilityDenied(frappe.PermissionError):
    """Raised when a user lacks the required CAPS capability."""

    def __init__(self, capability_code: str, user: str = None):
        self.capability_code = capability_code
        self.user = user or frappe.session.user
        super().__init__(
            _("You do not have the '{0}' capability. Contact your administrator.").format(
                capability_code
            )
        )


def check_capability(capability_code: str, user: str = None) -> bool:
    """Check if user has a specific CAPS capability. Returns True/False."""
    user = user or frappe.session.user

    if "System Manager" in frappe.get_roles(user):
        return True
    if user == "Administrator":
        return True
    if not frappe.db.exists("DocType", "CAPS Capability"):
        return True  # CAPS not installed = no gating

    return bool(
        frappe.db.exists(
            "CAPS User Capability",
            {"user": user, "capability": capability_code, "enabled": 1},
        )
    )


def require_capability(capability_code: str):
    """Decorator: ensure calling user has a CAPS capability."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not check_capability(capability_code):
                raise CapabilityDenied(capability_code)
            return fn(*args, **kwargs)
        return wrapper
    return decorator
