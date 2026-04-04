# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS Server-Side Enforcement
=============================

These functions are called from DocType controllers to enforce
field-level and action-level access on the server side.

SERVER-SIDE IS TRUTH — client-side CAPS is UX only.
"""

import re

import frappe
from frappe.utils import now_datetime


def filter_response_fields(doc):
    """
    Strip or mask restricted fields from a document's response.

    Call this from a DocType's on_load or after_load:
        def on_load(self):
            from caps.overrides import filter_response_fields
            filter_response_fields(self)
    """
    from caps.utils.resolver import get_field_restrictions

    user = frappe.session.user
    if user == "Administrator":
        return

    restrictions = get_field_restrictions(doc.doctype, user)
    if not restrictions:
        return

    for fieldname, rule in restrictions.items():
        if not hasattr(doc, fieldname):
            continue

        behavior = rule["behavior"]
        if behavior == "hide":
            doc.set(fieldname, None)
        elif behavior == "read_only":
            # Don't strip the value, but mark it read-only via flags
            doc.flags.caps_readonly_fields = doc.flags.get("caps_readonly_fields", [])
            doc.flags.caps_readonly_fields.append(fieldname)
        elif behavior == "mask":
            original = str(doc.get(fieldname) or "")
            if original:
                doc.set(fieldname, _apply_mask(original, rule.get("mask_pattern", "")))


def validate_field_write_permissions(doc):
    """
    Prevent writing to restricted fields on save.

    Call this from a DocType's before_save or validate:
        def before_save(self):
            from caps.overrides import validate_field_write_permissions
            validate_field_write_permissions(self)
    """
    from caps.utils.resolver import get_field_restrictions

    user = frappe.session.user
    if user == "Administrator":
        return

    restrictions = get_field_restrictions(doc.doctype, user)
    if not restrictions:
        return

    # Get the old values from DB
    if doc.is_new():
        return

    old_doc = doc.get_doc_before_save()
    if not old_doc:
        return

    for fieldname, rule in restrictions.items():
        behavior = rule["behavior"]
        if behavior in ("hide", "read_only"):
            old_val = old_doc.get(fieldname)
            new_val = doc.get(fieldname)
            if old_val != new_val:
                frappe.throw(
                    f"You do not have permission to modify field: {fieldname}",
                    frappe.PermissionError,
                )


def check_action_permission(doctype: str, action_id: str, user: str | None = None):
    """
    Check if a user can perform a specific action. Raises PermissionError if not.

    Usage:
        from caps.overrides import check_action_permission
        check_action_permission("Sales Order", "make_delivery")
    """
    from caps.utils.resolver import get_action_restrictions

    user = user or frappe.session.user
    if user == "Administrator":
        return

    restrictions = get_action_restrictions(doctype, user)
    for r in restrictions:
        if r["action_id"] == action_id:
            _audit_action_denied(user, doctype, action_id)
            frappe.throw(
                r.get("fallback_message") or f"You do not have permission for: {action_id}",
                frappe.PermissionError,
            )


def filter_export_fields(doctype: str, data: list[dict], user: str | None = None) -> list[dict]:
    """
    Mask/hide restricted fields in exported data (CSV, report, etc.).

    Usage in report or export code:
        from caps.overrides import filter_export_fields
        data = filter_export_fields("Customer", data)
    """
    from caps.utils.resolver import get_field_restrictions

    user = user or frappe.session.user
    if user == "Administrator":
        return data

    restrictions = get_field_restrictions(doctype, user)
    if not restrictions:
        return data

    for row in data:
        for fieldname, rule in restrictions.items():
            if fieldname not in row:
                continue
            behavior = rule["behavior"]
            if behavior == "hide":
                row[fieldname] = ""
            elif behavior == "mask":
                original = str(row.get(fieldname) or "")
                if original:
                    row[fieldname] = _apply_mask(original, rule.get("mask_pattern", ""))
    return data


# ─── Helpers ──────────────────────────────────────────────────────────


def _apply_mask(value: str, pattern: str) -> str:
    """
    Apply a mask pattern to a value.

    Patterns:
        "***{last4}"  → "***1234"
        "{first2}***" → "Ab***"
        "***"         → "***"
        ""            → "●●●●●"  (default)
    """
    if not pattern:
        return "●" * min(len(value), 8)

    result = pattern
    # {last4} → last 4 chars
    m = re.search(r"\{last(\d+)\}", pattern)
    if m:
        n = int(m.group(1))
        result = result.replace(m.group(0), value[-n:] if len(value) >= n else value)

    # {first2} → first 2 chars
    m = re.search(r"\{first(\d+)\}", pattern)
    if m:
        n = int(m.group(1))
        result = result.replace(m.group(0), value[:n] if len(value) >= n else value)

    return result


def _audit_action_denied(user: str, doctype: str, action_id: str):
    """Log denied action to audit trail."""
    try:
        frappe.get_doc({
            "doctype": "CAPS Audit Log",
            "user": user,
            "action": "capability_check",
            "capability": f"action:{doctype}:{action_id}",
            "result": "denied",
            "timestamp": now_datetime(),
            "ip_address": getattr(frappe.local, "request_ip", ""),
        }).insert(ignore_permissions=True)
    except Exception:
        pass
