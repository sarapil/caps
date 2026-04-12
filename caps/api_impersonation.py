# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS – Impersonation ("View As" / "Debug As")
===============================================

Lets a CAPS Admin temporarily assume another user's capability set for
debugging without switching sessions.

While impersonating:
  - resolve_capabilities() returns the *target* user's caps
  - boot session injects the target's restrictions
  - The original user retains their full system permissions
  - All actions are still audited under the real user

Impersonation state is stored in Redis (per session_id) with a configurable
TTL (default 30 min).  Closing the browser or calling stop_impersonation()
ends it.

Architecture:
  - api_impersonation.py      → start / stop / status endpoints
  - resolver.py               → checks impersonation in resolve_capabilities
  - boot.py                   → marks impersonation in bootinfo
  - caps_controller.js        → shows impersonation banner
"""

import frappe
from frappe.utils import now_datetime

_IMPERSONATION_TTL = 1800  # 30 minutes


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  PUBLIC API                                                          ║
# ╚═══════════════════════════════════════════════════════════════════════╝


@frappe.whitelist()
def start_impersonation(target_user: str) -> dict:
    frappe.only_for(["System Manager"])
def start_impersonation(target_user: str) -> dict:
    """
    Start impersonating another user's capabilities.

    The calling user must be CAPS Admin or System Manager.
    Only affects capability resolution — not Frappe permissions.

    Args:
        target_user: The user whose capabilities to assume.

    Returns:
        {status: "active", target_user: str, started_at: str}
    """
    frappe.only_for(["CAPS Manager", "System Manager"])


    real_user = frappe.session.user
    if real_user == target_user:
        frappe.throw("Cannot impersonate yourself")

    if not frappe.db.exists("User", target_user):
        frappe.throw(f"User {target_user} does not exist")

    # Check not already impersonating
    existing = get_impersonation_state(real_user)
    if existing:
        frappe.throw(
            f"Already impersonating {existing['target_user']}. "
            "Stop current impersonation first."
        )

    state = {
        "real_user": real_user,
        "target_user": target_user,
        "started_at": str(now_datetime()),
    }

    _set_impersonation_state(real_user, state)

    # Audit
    _audit_impersonation("impersonation_start", real_user, target_user)

    # Invalidate the real user's caps cache so resolver picks up impersonation
    from caps.utils.resolver import invalidate_user_cache
    invalidate_user_cache(real_user)

    return {"status": "active", **state}


@frappe.whitelist()
def stop_impersonation() -> dict:
    """
    Stop the current impersonation session.

    Returns:
        {status: "stopped"} or {status: "not_active"}
    """
    frappe.only_for(["CAPS Manager", "System Manager"])


    real_user = frappe.session.user
    state = get_impersonation_state(real_user)

    if not state:
        return {"status": "not_active"}

    target_user = state["target_user"]
    _clear_impersonation_state(real_user)

    # Audit
    _audit_impersonation("impersonation_end", real_user, target_user)

    # Invalidate so resolver returns the real user's caps again
    from caps.utils.resolver import invalidate_user_cache
    invalidate_user_cache(real_user)

    return {"status": "stopped", "was_impersonating": target_user}


@frappe.whitelist()
def get_impersonation_status() -> dict:
    """
    Check current impersonation state for the session user.

    Returns:
        {active: bool, target_user: str|None, started_at: str|None}
    """
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])

    state = get_impersonation_state(frappe.session.user)
    if state:
        return {
            "active": True,
            "target_user": state["target_user"],
            "started_at": state["started_at"],
        }
    return {"active": False, "target_user": None, "started_at": None}


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  STATE MANAGEMENT (Redis)                                            ║
# ╚═══════════════════════════════════════════════════════════════════════╝


def get_impersonation_state(user: str) -> dict | None:
    """
    Get the active impersonation state for a user (if any).
    Called by resolver.py — this is the integration point.
    """
    import json as _json
    raw = frappe.cache.get_value(f"caps:impersonate:{user}")
    if raw:
        if isinstance(raw, str):
            return _json.loads(raw)
        return raw
    return None


def _set_impersonation_state(user: str, state: dict):
    """Store impersonation state in Redis with TTL."""
    import json as _json
    frappe.cache.set_value(
        f"caps:impersonate:{user}",
        _json.dumps(state),
        expires_in_sec=_IMPERSONATION_TTL,
    )


def _clear_impersonation_state(user: str):
    """Remove impersonation state from Redis."""
    frappe.cache.delete_value(f"caps:impersonate:{user}")


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  HELPERS                                                             ║
# ╚═══════════════════════════════════════════════════════════════════════╝


def _audit_impersonation(action: str, real_user: str, target_user: str):
    """Log impersonation start/stop to audit trail."""
    try:
        frappe.get_doc({
            "doctype": "CAPS Audit Log",
            "user": real_user,
            "action": action,
            "target_user": target_user,
            "result": "allowed",
            "timestamp": now_datetime(),
            "ip_address": getattr(frappe.local, "request_ip", ""),
        }).insert(ignore_permissions=True)
    except Exception:
        pass
