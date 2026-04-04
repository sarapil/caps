# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS – Temporal Policy Engine
Applies and expires capability policies on schedule.
Called from hooks.py scheduler_events (daily) or via admin API.
"""

import frappe
from frappe.utils import now_datetime


# ── Apply active policies ─────────────────────────────────────────────
def apply_policies():
    """
    Scheduled task: iterate all active policies within their schedule window
    and ensure targeted users have the granted capabilities.
    Returns summary dict for admin API callers.
    """
    policies = frappe.get_all(
        "Capability Policy",
        filters={"is_active": 1},
        fields=["name"],
    )

    summary = {"applied": 0, "skipped": 0, "errors": []}

    for row in policies:
        try:
            doc = frappe.get_doc("Capability Policy", row.name)
            if not doc.is_currently_active():
                summary["skipped"] += 1
                continue

            users = doc.get_target_users()
            caps = doc.get_grant_items()

            for user in users:
                for cap_name in caps:
                    granted = _ensure_user_has_capability(
                        user, cap_name, policy_name=doc.name, expires_on=doc.ends_on
                    )
                    if granted:
                        summary["applied"] += 1
        except Exception as e:
            summary["errors"].append({"policy": row.name, "error": str(e)})
            frappe.log_error(
                title=f"CAPS Policy Error: {row.name}",
                message=frappe.get_traceback(),
            )

    frappe.db.commit()
    return summary


# ── Expire ended policies ─────────────────────────────────────────────
def expire_policies():
    """
    Scheduled task: find policies past their ends_on and revoke
    the capabilities they granted (identified via source='policy:<name>').
    """
    current = now_datetime()
    expired = frappe.get_all(
        "Capability Policy",
        filters={
            "is_active": 1,
            "ends_on": ["<", current],
            "ends_on": ["is", "set"],
        },
        fields=["name"],
    )

    summary = {"expired": 0, "errors": []}

    for row in expired:
        try:
            doc = frappe.get_doc("Capability Policy", row.name)
            users = doc.get_target_users()
            caps = doc.get_grant_items()

            for user in users:
                for cap_name in caps:
                    revoked = _revoke_policy_grant(user, cap_name, doc.name)
                    if revoked:
                        summary["expired"] += 1

            # Mark policy inactive after expiry processing
            frappe.db.set_value("Capability Policy", doc.name, "is_active", 0)

            _audit_policy("policy_expired", doc.name)
        except Exception as e:
            summary["errors"].append({"policy": row.name, "error": str(e)})
            frappe.log_error(
                title=f"CAPS Policy Expiry Error: {row.name}",
                message=frappe.get_traceback(),
            )

    frappe.db.commit()
    return summary


# ── Preview policy impact ──────────────────────────────────────────────
def preview_policy(policy_name):
    """Return which users would be affected and what capabilities granted."""
    doc = frappe.get_doc("Capability Policy", policy_name)
    users = doc.get_target_users()
    caps = doc.get_grant_items()

    already_have = []
    would_grant = []

    for user in users:
        user_caps = _get_user_direct_caps(user)
        for cap_name in caps:
            entry = {"user": user, "capability": cap_name}
            if cap_name in user_caps:
                already_have.append(entry)
            else:
                would_grant.append(entry)

    return {
        "policy": policy_name,
        "is_active": doc.is_currently_active(),
        "target_users_count": len(users),
        "capabilities_count": len(caps),
        "would_grant": would_grant,
        "already_have": already_have,
    }


# ── Internal helpers ───────────────────────────────────────────────────
def _ensure_user_has_capability(user, capability, policy_name=None, expires_on=None):
    """
    Grant capability to user if they don't already have it as a direct grant.
    Tags the grant with policy source for later cleanup.
    Returns True if a new grant was made.
    """
    uc = frappe.db.get_value("User Capability", {"user": user}, "name")

    if uc:
        existing = frappe.get_all(
            "User Capability Item",
            filters={"parent": uc, "capability": capability},
            fields=["name"],
        )
        if existing:
            return False  # Already has this capability

        doc = frappe.get_doc("User Capability", uc)
    else:
        doc = frappe.new_doc("User Capability")
        doc.user = user
        doc.insert(ignore_permissions=True)

    doc.append("direct_capabilities", {
        "capability": capability,
        "granted_by": "Administrator",
        "granted_on": now_datetime(),
        "expires_on": expires_on,
        "notes": f"policy:{policy_name}" if policy_name else None,
    })
    doc.save(ignore_permissions=True)

    # Invalidate cache
    _invalidate_user_cache(user)

    _audit_policy("policy_applied", policy_name, user=user, capability=capability)
    return True


def _revoke_policy_grant(user, capability, policy_name):
    """
    Revoke a capability that was granted by a specific policy.
    Only removes grants tagged with 'policy:<policy_name>' in notes.
    Returns True if a grant was revoked.
    """
    uc = frappe.db.get_value("User Capability", {"user": user}, "name")
    if not uc:
        return False

    tag = f"policy:{policy_name}"
    items = frappe.get_all(
        "User Capability Item",
        filters={
            "parent": uc,
            "capability": capability,
            "notes": tag,
        },
        fields=["name"],
    )

    if not items:
        return False

    for item in items:
        frappe.delete_doc("User Capability Item", item.name, ignore_permissions=True)

    _invalidate_user_cache(user)
    return True


def _get_user_direct_caps(user):
    """Get set of capability names directly granted to user."""
    uc = frappe.db.get_value("User Capability", {"user": user}, "name")
    if not uc:
        return set()
    items = frappe.get_all(
        "User Capability Item",
        filters={"parent": uc},
        fields=["capability"],
        pluck="capability",
    )
    return set(items)


def _invalidate_user_cache(user):
    """Clear CAPS cache for a user."""
    try:
        from caps.cache_invalidation import invalidate_for_user
        invalidate_for_user(user)
    except ImportError:
        cache_key = f"caps:user:{user}"
        frappe.cache.delete_value(cache_key)


def _audit_policy(action, policy_name, user=None, capability=None):
    """Create audit log entry for policy actions."""
    try:
        frappe.get_doc({
            "doctype": "CAPS Audit Log",
            "action": action,
            "user": user or frappe.session.user,
            "capability": capability,
            "performed_by": "Administrator",
            "details": f"Policy: {policy_name}",
        }).insert(ignore_permissions=True)
    except Exception:
        pass  # Don't break policy engine for audit failures
