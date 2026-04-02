"""
CAPS – Policy Management API
Endpoints for managing temporal capability policies.
All endpoints require CAPS Admin or System Manager role.
"""

import frappe


# ── Policy CRUD helpers (beyond standard DocType API) ──────────────────

@frappe.whitelist()
def preview_policy(policy_name):
    """Preview which users and capabilities a policy would affect."""
    frappe.only_for(["System Manager", "CAPS Admin", "CAPS User"])
    from caps.policy_engine import preview_policy as _preview
    return _preview(policy_name)


@frappe.whitelist()
def apply_policy_now(policy_name):
    """Manually trigger a single policy application (admin action)."""

    doc = frappe.get_doc("Capability Policy", policy_name)
    if not doc.is_currently_active():
        frappe.throw(f"Policy '{policy_name}' is not currently active or within schedule")

    users = doc.get_target_users()
    caps = doc.get_grant_items()

    from caps.policy_engine import _ensure_user_has_capability

    granted = 0
    for user in users:
        for cap_name in caps:
            if _ensure_user_has_capability(user, cap_name, policy_name=doc.name, expires_on=doc.ends_on):
                granted += 1

    frappe.db.commit()
    return {"policy": policy_name, "granted": granted, "target_users": len(users)}


@frappe.whitelist()
def apply_all_policies():
    """Manually trigger all policy applications (admin action)."""
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])

    from caps.policy_engine import apply_policies
    return apply_policies()


@frappe.whitelist()
def expire_all_policies():
    """Manually trigger policy expiry processing."""
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])

    from caps.policy_engine import expire_policies
    return expire_policies()


@frappe.whitelist()
def get_policy_status(policy_name):
    """Get detailed status of a policy including affected user counts."""
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    doc = frappe.get_doc("Capability Policy", policy_name)
    users = doc.get_target_users()
    caps = doc.get_grant_items()

    # Count how many target users already have the grants
    granted_count = 0
    for user in users:
        from caps.policy_engine import _get_user_direct_caps
        user_caps = _get_user_direct_caps(user)
        for cap_name in caps:
            if cap_name in user_caps:
                granted_count += 1

    total_possible = len(users) * len(caps)

    return {
        "policy": policy_name,
        "is_active": doc.is_active,
        "is_currently_active": doc.is_currently_active(),
        "target_type": doc.target_type,
        "target_users_count": len(users),
        "capabilities_count": len(caps),
        "grants_existing": granted_count,
        "grants_remaining": total_possible - granted_count,
        "starts_on": str(doc.starts_on) if doc.starts_on else None,
        "ends_on": str(doc.ends_on) if doc.ends_on else None,
    }


@frappe.whitelist()
def get_active_policies():
    """List all currently active policies with summary info."""
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    policies = frappe.get_all(
        "Capability Policy",
        filters={"is_active": 1},
        fields=[
            "name", "policy_name", "target_type", "grant_type",
            "capability", "bundle", "starts_on", "ends_on", "priority",
        ],
        order_by="priority desc, modified desc",
    )

    return policies
