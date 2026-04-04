# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
User Access Matrix Report
=========================

Shows a users × capabilities matrix:
each row = user, each column = capability.
Cells indicate the source: D(irect), G(roup), R(ole), or blank.

Supports filtering by user, capability, and assignment channel.
"""

import frappe
from frappe import _


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns, data = get_matrix(filters)
    return columns, data


def get_matrix(filters):
    # Determine users to include
    user_filter = {}
    if filters.get("user"):
        user_filter["name"] = filters["user"]

    users = frappe.get_all(
        "User",
        filters={**user_filter, "enabled": 1, "user_type": "System User"},
        fields=["name", "full_name"],
        order_by="full_name",
        limit_page_length=200,
    )

    if not users:
        return [{"label": _("User"), "fieldtype": "Data", "fieldname": "user", "width": 200}], []

    # Determine capabilities to include
    cap_filter = {"is_active": 1}
    if filters.get("capability"):
        cap_filter["name"] = filters["capability"]
    if filters.get("category"):
        cap_filter["category"] = filters["category"]

    capabilities = frappe.get_all(
        "Capability",
        filters=cap_filter,
        fields=["name", "label"],
        order_by="name",
        limit_page_length=100,
    )

    if not capabilities:
        return [{"label": _("User"), "fieldtype": "Data", "fieldname": "user", "width": 200}], []

    # Build columns: User + one column per capability
    columns = [
        {"label": _("User"), "fieldtype": "Link", "fieldname": "user",
         "options": "User", "width": 200},
        {"label": _("Full Name"), "fieldtype": "Data", "fieldname": "full_name",
         "width": 180},
    ]

    cap_names = [c["name"] for c in capabilities]
    for cap in capabilities:
        short_label = cap["label"][:20] if cap["label"] else cap["name"][:20]
        columns.append({
            "label": _(short_label),
            "fieldtype": "Data",
            "fieldname": cap["name"],
            "width": 80,
        })

    # Pre-load all assignment data
    user_names = [u["name"] for u in users]

    # Direct assignments
    direct = _load_assignments(
        "User Capability Item", "parent", "capability", user_names, cap_names
    )

    # Group assignments (via Permission Group Member → Permission Group Capability)
    group = _load_group_assignments(user_names, cap_names)

    # Role assignments (via Has Role → Role Capability Map → Role Capability Item)
    role = _load_role_assignments(user_names, cap_names)

    # Build matrix rows
    channel_filter = filters.get("channel")
    data = []
    for u in users:
        row = {"user": u["name"], "full_name": u["full_name"]}
        has_any = False

        for cap_name in cap_names:
            sources = []
            if (u["name"], cap_name) in direct:
                sources.append("D")
            if (u["name"], cap_name) in group:
                sources.append("G")
            if (u["name"], cap_name) in role:
                sources.append("R")

            # Apply channel filter
            if channel_filter:
                channel_map = {"Direct": "D", "Group": "G", "Role": "R"}
                wanted = channel_map.get(channel_filter)
                if wanted and wanted not in sources:
                    sources = []

            cell = "/".join(sources) if sources else ""
            row[cap_name] = cell
            if cell:
                has_any = True

        if has_any or not filters.get("hide_empty"):
            data.append(row)

    return columns, data


def _load_assignments(doctype, parent_field, cap_field, users, caps):
    """Load direct user→capability assignments as a set of (user, cap) tuples."""
    result = set()
    rows = frappe.get_all(
        doctype,
        filters={parent_field: ("in", users), cap_field: ("in", caps)},
        fields=[parent_field, cap_field],
    )
    for r in rows:
        result.add((r[parent_field], r[cap_field]))
    return result


def _load_group_assignments(users, caps):
    """Load group-based assignments as (user, cap) tuples."""
    result = set()

    # Get group memberships for these users
    memberships = frappe.get_all(
        "Permission Group Member",
        filters={"user": ("in", users)},
        fields=["user", "parent"],
    )
    if not memberships:
        return result

    user_groups = {}
    for m in memberships:
        user_groups.setdefault(m["user"], []).append(m["parent"])

    group_names = list({m["parent"] for m in memberships})

    # Get capabilities per group
    group_caps = frappe.get_all(
        "Permission Group Capability",
        filters={"parent": ("in", group_names), "capability": ("in", caps)},
        fields=["parent", "capability"],
    )
    group_cap_map = {}
    for gc in group_caps:
        group_cap_map.setdefault(gc["parent"], set()).add(gc["capability"])

    for user, groups in user_groups.items():
        for g in groups:
            for c in group_cap_map.get(g, set()):
                result.add((user, c))

    return result


def _load_role_assignments(users, caps):
    """Load role-based assignments as (user, cap) tuples."""
    result = set()

    # Get roles for these users
    has_roles = frappe.get_all(
        "Has Role",
        filters={"parent": ("in", users), "parenttype": "User"},
        fields=["parent", "role"],
    )
    if not has_roles:
        return result

    user_roles = {}
    for hr in has_roles:
        user_roles.setdefault(hr["parent"], set()).add(hr["role"])

    all_roles = list({hr["role"] for hr in has_roles})

    # Get Role Capability Maps for these roles
    role_maps = frappe.get_all(
        "Role Capability Map",
        filters={"role": ("in", all_roles)},
        fields=["name", "role"],
    )
    if not role_maps:
        return result

    role_map_names = [rm["name"] for rm in role_maps]
    role_to_map = {rm["name"]: rm["role"] for rm in role_maps}

    # Get capabilities from role maps
    role_items = frappe.get_all(
        "Role Capability Item",
        filters={"parent": ("in", role_map_names), "capability": ("in", caps)},
        fields=["parent", "capability"],
    )

    role_cap_map = {}
    for ri in role_items:
        role = role_to_map.get(ri["parent"])
        if role:
            role_cap_map.setdefault(role, set()).add(ri["capability"])

    for user, roles in user_roles.items():
        for r in roles:
            for c in role_cap_map.get(r, set()):
                result.add((user, c))

    return result
