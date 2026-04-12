# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS Delegation API
====================

Endpoints for CAPS Managers to delegate capabilities they hold
to other users. Delegation is scoped: a manager can only delegate
capabilities that are:
  1. Marked as ``is_delegatable`` on the Capability DocType
  2. In the manager's own resolved capability set

This enables a self-service model where team leads can grant
permissions without needing System Manager access.
"""

import frappe
from frappe.utils import now_datetime


@frappe.whitelist()
def delegate_capability(
    user: str,
    capability: str,
    expires_on: str | None = None,
    reason: str | None = None,
) -> dict:
    frappe.only_for(["System Manager"])
    """
    Delegate a capability to another user.

    The calling user must:
    - Have the CAPS Manager role (or System Manager / CAPS Admin)
    - Hold the capability themselves
    - The capability must be marked as ``is_delegatable``
    - Delegation must be enabled in CAPS Settings
    """
    frappe.only_for(["System Manager", "CAPS Admin", "CAPS Manager"])

    from caps.settings_helper import get_caps_settings
    settings = get_caps_settings()

    if not settings.enable_delegation:
        frappe.throw("Delegation is disabled in CAPS Settings")

    if settings.require_delegation_reason and not reason:
        frappe.throw("A reason is required for delegation")

    # Validate capability exists and is delegatable
    if not frappe.db.exists("Capability", capability):
        frappe.throw(f"Capability '{capability}' does not exist")

    cap_doc = frappe.get_doc("Capability", capability)
    if not cap_doc.is_delegatable:
        frappe.throw(f"Capability '{capability}' is not marked as delegatable")

    if not cap_doc.is_active:
        frappe.throw(f"Capability '{capability}' is inactive")

    # Check that the delegator holds this capability
    from caps.utils.resolver import resolve_capabilities
    delegator = frappe.session.user
    delegator_caps = resolve_capabilities(delegator)

    if capability not in delegator_caps:
        frappe.throw(
            f"You do not hold capability '{capability}' and cannot delegate it"
        )

    # Validate target user exists
    if not frappe.db.exists("User", user):
        frappe.throw(f"User '{user}' does not exist")

    if user == delegator:
        frappe.throw("Cannot delegate a capability to yourself")

    # Ensure User Capability doc exists
    if not frappe.db.exists("User Capability", user):
        frappe.get_doc({
            "doctype": "User Capability",
            "user": user,
        }).insert(ignore_permissions=True)

    doc = frappe.get_doc("User Capability", user)

    # Check not already granted
    for row in doc.direct_capabilities:
        if row.capability == capability:
            frappe.throw(f"User already has capability: {capability}")

    doc.append("direct_capabilities", {
        "capability": capability,
        "granted_by": delegator,
        "granted_on": now_datetime(),
        "expires_on": expires_on or None,
        "delegated_by": delegator,
    })
    doc.save(ignore_permissions=True)

    from caps.utils.resolver import invalidate_user_cache
    invalidate_user_cache(user)

    # Audit
    _audit_delegation("delegation_granted", delegator, user, capability, reason)

    # Notify the delegatee
    from caps.notifications import notify_delegation
    notify_delegation(delegator, user, capability, action="granted")

    return {"status": "delegated", "capability": capability, "user": user}


@frappe.whitelist()
def revoke_delegated(user: str, capability: str) -> dict:
    """
    Revoke a capability that was delegated by the current user.

    A CAPS Manager can only revoke grants that they personally delegated
    (identified by ``delegated_by`` field). System Manager / CAPS Admin
    can revoke any delegation.
    """
    frappe.only_for(["System Manager", "CAPS Admin", "CAPS Manager"])

    if not frappe.db.exists("User Capability", user):
        frappe.throw(f"No User Capability record for: {user}")

    doc = frappe.get_doc("User Capability", user)
    revoker = frappe.session.user
    is_admin = "System Manager" in frappe.get_roles(revoker) or "CAPS Admin" in frappe.get_roles(revoker)

    found = False
    for row in doc.direct_capabilities:
        if row.capability == capability:
            # CAPS Managers can only revoke their own delegations
            if not is_admin and row.delegated_by != revoker:
                frappe.throw(
                    f"You can only revoke capabilities you delegated. "
                    f"This was delegated by: {row.delegated_by or 'admin grant'}"
                )
            doc.remove(row)
            found = True
            break

    if not found:
        frappe.throw(f"User does not have direct capability: {capability}")

    doc.save(ignore_permissions=True)

    from caps.utils.resolver import invalidate_user_cache
    invalidate_user_cache(user)

    _audit_delegation("delegation_revoked", revoker, user, capability)
    return {"status": "revoked", "capability": capability, "user": user}


@frappe.whitelist()
def get_delegatable_capabilities() -> list[dict]:
    """
    Return all capabilities the current user can delegate.

    A capability is delegatable if:
    1. It's marked ``is_delegatable`` on the Capability DocType
    2. The current user holds it in their resolved set
    """
    frappe.only_for(["System Manager", "CAPS Admin", "CAPS User"])
    from caps.utils.resolver import resolve_capabilities

    user_caps = resolve_capabilities(frappe.session.user)

    delegatable = frappe.get_all(
        "Capability",
        filters={"is_active": 1, "is_delegatable": 1},
        fields=["name", "label", "category"],
    )

    return [
        cap for cap in delegatable
        if cap["name"] in user_caps
    ]


@frappe.whitelist()
def get_my_delegations() -> list[dict]:
    """
    Return all capabilities the current user has delegated to others.
    """
    frappe.only_for(["System Manager", "CAPS Admin", "CAPS User"])
    delegator = frappe.session.user

    rows = frappe.get_all(
        "User Capability Item",
        filters={"delegated_by": delegator},
        fields=["parent as user", "capability", "granted_on", "expires_on"],
        order_by="granted_on desc",
    )
    return rows


# ─── Helpers ──────────────────────────────────────────────────────────


def _audit_delegation(action: str, delegator: str, target_user: str, capability: str, reason: str | None = None):
    """Log delegation event."""
    try:
        context = {"delegator": delegator}
        if reason:
            context["reason"] = reason
        frappe.get_doc({
            "doctype": "CAPS Audit Log",
            "user": delegator,
            "action": action,
            "capability": capability,
            "target_user": target_user,
            "result": "allowed",
            "context": frappe.as_json(context),
            "timestamp": now_datetime(),
            "ip_address": getattr(frappe.local, "request_ip", ""),
        }).insert(ignore_permissions=True)
    except Exception:
        pass
