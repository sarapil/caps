# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS – Automatic Document Permission Hooks
============================================

Zero-config integration: when Field Capability Maps or Action Capability Maps
exist for a DocType, CAPS automatically enforces them via doc_events, without
the developer needing to add explicit calls in every controller.

Hooks wired in hooks.py:
  doc_events["*"]:
    - on_load    → auto_filter_fields
    - before_save → auto_validate_writes
  has_permission:
    - caps.hooks_integration.has_permission  (for action maps)
  on_session_creation:
    - caps.hooks_integration.on_login_audit
"""

import frappe
from frappe.utils import now_datetime


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  WILDCARD DOC EVENTS                                                 ║
# ╚═══════════════════════════════════════════════════════════════════════╝


def auto_filter_fields(doc, method=None):
    """
    Automatically filter restricted fields on document load.
    Wired as doc_events["*"]["on_load"].
    """
    if not _should_enforce():
        return

    user = frappe.session.user
    if user == "Administrator":
        return

    from caps.utils.resolver import get_field_restrictions

    restrictions = get_field_restrictions(doc.doctype, user)
    if not restrictions:
        return

    from caps.overrides import filter_response_fields
    filter_response_fields(doc)


def auto_validate_writes(doc, method=None):
    """
    Automatically validate field write permissions before save.
    Wired as doc_events["*"]["before_save"].
    """
    if not _should_enforce():
        return

    user = frappe.session.user
    if user == "Administrator":
        return

    from caps.utils.resolver import get_field_restrictions

    restrictions = get_field_restrictions(doc.doctype, user)
    if not restrictions:
        return

    from caps.overrides import validate_field_write_permissions
    validate_field_write_permissions(doc)


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  LOGIN AUDIT                                                         ║
# ╚═══════════════════════════════════════════════════════════════════════╝


def on_login_audit(login_manager):
    """
    Audit login event: log the user's capability count at login time.
    Wired as on_session_creation hook.
    """
    if not _should_enforce():
        return

    user = login_manager.user
    if user in ("Administrator", "Guest"):
        return

    try:
        from caps.utils.resolver import resolve_capabilities
        caps = resolve_capabilities(user)

        frappe.get_doc({
            "doctype": "CAPS Audit Log",
            "user": user,
            "action": "capability_check",
            "capability": f"login:count={len(caps)}",
            "result": "allowed",
            "timestamp": now_datetime(),
            "ip_address": getattr(frappe.local, "request_ip", ""),
            "context": frappe.as_json({
                "event": "login",
                "capability_count": len(caps),
            }),
        }).insert(ignore_permissions=True)
    except Exception:
        pass  # Never break login for audit failures


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  PERMISSION QUERY CONDITIONS                                         ║
# ╚═══════════════════════════════════════════════════════════════════════╝


def get_caps_permission_query(doctype: str, user: str | None = None) -> str:
    """
    Return SQL WHERE clause to filter list views based on CAPS.

    This is a helper that can be wired into hooks.py as:
        permission_query_conditions = {
            "DocType": "caps.hooks_integration.get_caps_permission_query"
        }

    For now, returns empty string (no list filtering) — the framework is
    here for future DocType-level capability gating.
    """
    return ""


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  HELPERS                                                             ║
# ╚═══════════════════════════════════════════════════════════════════════╝


def _should_enforce() -> bool:
    """Check if CAPS is enabled and should enforce rules."""
    try:
        from caps.settings_helper import get_caps_settings
        return bool(get_caps_settings().enable_caps)
    except Exception:
        return False
