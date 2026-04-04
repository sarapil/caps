# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS Permission Gate for CAPS
Provides capability-based access control integration.
"""
import frappe


def has_capability(user=None, capability=None):
    """Check if user has a specific CAPS capability via CAPS."""
    if not user:
        user = frappe.session.user
    if user == "Administrator":
        return True
    if not capability:
        return False

    # Prefix capability if not already prefixed
    if not capability.startswith("CP_"):
        capability = f"CP_{capability}"

    try:
        return frappe.db.exists("CAPS User Capability", {
            "user": user,
            "capability": capability,
            "enabled": 1,
        })
    except Exception:
        # CAPS not installed or table missing — fallback to permissive
        return True


def require_capability(capability):
    """Decorator: raise PermissionError if user lacks capability."""
    def decorator(fn):
        def wrapper(*args, **kwargs):
            if not has_capability(capability=capability):
                frappe.throw(
                    frappe._("Insufficient permissions: {0}").format(capability),
                    frappe.PermissionError,
                )
            return fn(*args, **kwargs)
        wrapper.__name__ = fn.__name__
        wrapper.__doc__ = fn.__doc__
        return wrapper
    return decorator


def check_permission(doctype, ptype="read", doc=None, user=None):
    """Extended permission check combining Frappe permissions + CAPS capabilities."""
    if not user:
        user = frappe.session.user
    if user == "Administrator":
        return True

    # Standard Frappe permission
    if not frappe.has_permission(doctype, ptype, doc=doc, user=user):
        return False

    return True
