# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS — Validators
Input validation utilities for CAPS.
"""

import re
import frappe
from frappe import _


def validate_required(value, field_label: str):
    """Raise if value is empty/None."""
    if not value:
        frappe.throw(_("{0} is required").format(_(field_label)))


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email or ""):
        frappe.throw(_("Invalid email address: {0}").format(email))
    return True


def validate_phone(phone: str) -> bool:
    """Validate phone number (international format)."""
    pattern = r"^\+?[1-9]\d{6,14}$"
    cleaned = re.sub(r"[\s\-()]", "", phone or "")
    if not re.match(pattern, cleaned):
        frappe.throw(_("Invalid phone number: {0}").format(phone))
    return True


def validate_positive_number(value, field_label: str):
    """Ensure numeric value is > 0."""
    try:
        num = float(value)
    except (TypeError, ValueError):
        frappe.throw(_("{0} must be a number").format(_(field_label)))
        return
    if num <= 0:
        frappe.throw(_("{0} must be greater than zero").format(_(field_label)))


def validate_in_list(value, valid_options: list, field_label: str):
    """Ensure value is one of the allowed options."""
    if value not in valid_options:
        frappe.throw(
            _("{0} must be one of: {1}").format(_(field_label), ", ".join(str(o) for o in valid_options))
        )


def sanitize_html(value: str) -> str:
    """Sanitize HTML to prevent XSS."""
    return frappe.utils.sanitize_html(value) if value else ""
