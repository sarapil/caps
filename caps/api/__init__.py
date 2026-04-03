"""
CAPS Public API
===============

Whitelisted endpoints for client-side CAPS operations.
"""

import frappe
from frappe.utils import now_datetime


@frappe.whitelist()
def check_capability(capability: str) -> bool:
    """Check if the current user has a specific capability."""
    frappe.only_for(["System Manager", "CAPS Admin", "CAPS User"])
    from caps.utils.resolver import has_capability
    return has_capability(capability)


@frappe.whitelist()
def check_capabilities(capabilities: str | list) -> dict:
    """
    Check multiple capabilities at once.
    Returns {capability: True/False}.
    """
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])

    from caps.utils.resolver import resolve_capabilities

    if isinstance(capabilities, str):
        import json
        capabilities = json.loads(capabilities)

    user_caps = resolve_capabilities(frappe.session.user)
    return {cap: (cap in user_caps) for cap in capabilities}


@frappe.whitelist()
def get_my_capabilities() -> list[str]:
    """Return list of all capabilities for the current user."""
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])

    from caps.utils.resolver import resolve_capabilities
    return sorted(resolve_capabilities(frappe.session.user))


@frappe.whitelist()
def get_restrictions(doctype: str) -> dict:
    """
    Return field + action restrictions for the current user on a doctype.
    Called by frappe.caps.getRestrictions() on the client.
    """
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])

    from caps.utils.resolver import get_action_restrictions, get_field_restrictions

    return {
        "fields": get_field_restrictions(doctype),
        "actions": get_action_restrictions(doctype),
    }


@frappe.whitelist()
def get_dependency_graph(capability: str | None = None) -> dict:
    """
    Return the dependency graph for a capability (or all capabilities).
    Returns {nodes: [...], edges: [...]} for visualization.
    """
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])

    from caps.utils.resolver import get_dependency_graph as _get_graph
    return _get_graph(capability)


@frappe.whitelist()
def check_prerequisites(capability: str, user: str | None = None) -> dict:
    """
    Check whether all prerequisites for a capability are met for a user.
    Returns {met: bool, missing: [str], capability: str}.
    """
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])

    from caps.utils.resolver import resolve_capabilities

    user = user or frappe.session.user
    if user != frappe.session.user:
        frappe.only_for(["System Manager", "CAPS Manager"])

    user_caps = resolve_capabilities(user)

    # Get direct prerequisites
    prereqs = frappe.get_all(
        "Capability Prerequisite",
        filters={"parent": capability, "parenttype": "Capability", "is_hard": 1},
        pluck="prerequisite",
    )

    missing = [p for p in prereqs if p not in user_caps]
    return {
        "capability": capability,
        "user": user,
        "met": len(missing) == 0,
        "missing": missing,
        "total_prerequisites": len(prereqs),
    }


@frappe.whitelist()
def get_all_restrictions() -> dict:
    """
    Return ALL field + action restrictions for current user.
    Used for client-side cache refresh.
    """
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])

    from caps.utils.resolver import (
        get_action_restrictions_all,
        get_field_restrictions_all,
    )

    return {
        "field_restrictions": get_field_restrictions_all(),
        "action_restrictions": get_action_restrictions_all(),
        "version": int(frappe.cache.get_value("caps:map_version") or 0),
    }


@frappe.whitelist()
def bust_cache():
    """Force-refresh the current user's capability cache."""
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])

    from caps.utils.resolver import invalidate_user_cache
    invalidate_user_cache(frappe.session.user)
    return {"status": "ok"}


# ─── Admin-Only Endpoints ────────────────────────────────────────────


@frappe.whitelist()
def get_user_capabilities(user: str) -> dict:
    """
    Admin tool: get full capability breakdown for any user.
    Shows which capabilities come from which channel.
    """
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    from caps.utils.resolver import (
        _all_active_capability_names,
        _collect_direct_user,
        _collect_from_groups,
        _collect_from_roles,
        resolve_capabilities,
    )

    now = now_datetime()
    active = _all_active_capability_names()

    direct = _collect_direct_user(user, now, active)
    groups = _collect_from_groups(user, active)
    roles = _collect_from_roles(user, active)
    total = resolve_capabilities(user)

    return {
        "user": user,
        "total_count": len(total),
        "direct": sorted(direct),
        "from_groups": sorted(groups),
        "from_roles": sorted(roles),
        "all": sorted(total),
    }


@frappe.whitelist()
def compare_users(user1: str, user2: str) -> dict:
    """
    Admin tool: compare capabilities between two users.
    Returns shared, only_user1, only_user2.
    """
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    from caps.utils.resolver import resolve_capabilities

    caps1 = resolve_capabilities(user1)
    caps2 = resolve_capabilities(user2)

    return {
        "user1": user1,
        "user2": user2,
        "shared": sorted(caps1 & caps2),
        "only_user1": sorted(caps1 - caps2),
        "only_user2": sorted(caps2 - caps1),
    }


@frappe.whitelist()
def grant_capability(user: str, capability: str, expires_on: str | None = None):
    """Admin tool: grant a capability directly to a user."""
    frappe.only_for(["CAPS Manager", "System Manager"])


    from caps.utils.resolver import invalidate_user_cache, resolve_capabilities

    if not frappe.db.exists("Capability", capability):
        frappe.throw(f"Capability '{capability}' does not exist")

    # Check if the user has all hard prerequisites for this capability
    prereqs = frappe.get_all(
        "Capability Prerequisite",
        filters={"parent": capability, "parenttype": "Capability", "is_hard": 1},
        pluck="prerequisite",
    )
    if prereqs:
        user_caps = resolve_capabilities(user)
        missing = [p for p in prereqs if p not in user_caps]
        if missing:
            frappe.throw(
                f"Cannot grant '{capability}': missing prerequisites: {', '.join(missing)}"
            )

    if not frappe.db.exists("User Capability", user):
        doc = frappe.get_doc({
            "doctype": "User Capability",
            "user": user,
        })
        doc.insert(ignore_permissions=True)

    doc = frappe.get_doc("User Capability", user)
    # Check if already assigned
    for row in doc.direct_capabilities:
        if row.capability == capability:
            frappe.throw(f"User already has capability: {capability}")

    doc.append("direct_capabilities", {
        "capability": capability,
        "granted_by": frappe.session.user,
        "granted_on": now_datetime(),
        "expires_on": expires_on or None,
    })
    doc.save(ignore_permissions=True)
    invalidate_user_cache(user)

    # Audit
    frappe.get_doc({
        "doctype": "CAPS Audit Log",
        "user": frappe.session.user,
        "action": "capability_granted",
        "capability": capability,
        "target_user": user,
        "result": "allowed",
        "timestamp": now_datetime(),
        "ip_address": getattr(frappe.local, "request_ip", ""),
    }).insert(ignore_permissions=True)

    return {"status": "granted"}


@frappe.whitelist()
def revoke_capability(user: str, capability: str):
    """Admin tool: revoke a directly-assigned capability from a user."""
    frappe.only_for(["CAPS Manager", "System Manager"])


    from caps.utils.resolver import invalidate_user_cache

    if not frappe.db.exists("User Capability", user):
        frappe.throw(f"No User Capability record for: {user}")

    doc = frappe.get_doc("User Capability", user)
    found = False
    for row in doc.direct_capabilities:
        if row.capability == capability:
            doc.remove(row)
            found = True
            break

    if not found:
        frappe.throw(f"User does not have direct capability: {capability}")

    doc.save(ignore_permissions=True)
    invalidate_user_cache(user)

    # Audit
    frappe.get_doc({
        "doctype": "CAPS Audit Log",
        "user": frappe.session.user,
        "action": "capability_revoked",
        "capability": capability,
        "target_user": user,
        "result": "allowed",
        "timestamp": now_datetime(),
        "ip_address": getattr(frappe.local, "request_ip", ""),
    }).insert(ignore_permissions=True)

    return {"status": "revoked"}


@frappe.whitelist()
def get_capability_tree(root: str | None = None) -> dict:
    """
    Return the capability hierarchy as a tree.

    Args:
        root: Optional root capability name.  If omitted, returns the full forest.

    Returns:
        {nodes: [{name, label, parent, children: [...]}, ...]}
    """
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])

    all_caps = frappe.get_all(
        "Capability",
        fields=["name", "name1", "label", "parent_capability", "is_active", "category"],
    )

    # Build lookup
    by_name = {c["name"]: c for c in all_caps}
    children_map: dict[str, list] = {}
    roots: list[dict] = []

    for c in all_caps:
        parent = c.get("parent_capability")
        if parent and parent in by_name:
            children_map.setdefault(parent, []).append(c["name"])
        else:
            roots.append(c)

    def _build(name):
        node = by_name[name]
        return {
            "name": node["name"],
            "label": node["label"],
            "category": node["category"],
            "is_active": node["is_active"],
            "parent": node.get("parent_capability"),
            "children": [_build(ch) for ch in children_map.get(name, [])],
        }

    if root:
        if root not in by_name:
            frappe.throw(f"Capability {root} not found")
        return {"nodes": [_build(root)]}

    return {"nodes": [_build(r["name"]) for r in roots]}
