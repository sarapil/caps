"""
CAPS Group Hierarchy API
========================

Endpoints for managing Permission Group hierarchy, tree views,
temporary membership, and ancestor/descendant queries.

All endpoints require System Manager or CAPS Admin role.
"""

import frappe
from frappe.utils import now_datetime


@frappe.whitelist()
def get_group_tree() -> list[dict]:
    """
    Return the full Permission Group tree as a nested list.

    Each node: {name, label, parent_group, member_count, capability_count, children: []}

    Returns top-level groups (no parent) with children nested recursively.
    """
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    groups = frappe.get_all(
        "Permission Group",
        fields=["name", "label", "parent_group"],
    )

    # Count members per group
    member_counts = {}
    members = frappe.db.sql(
        "SELECT parent, COUNT(name) as cnt FROM `tabPermission Group Member` GROUP BY parent",
        as_dict=True,
    )
    for m in members:
        member_counts[m["parent"]] = m["cnt"]

    # Count capabilities per group (child table name is "Permission Group Capability")
    cap_counts = {}
    caps = frappe.db.sql(
        "SELECT parent, COUNT(name) as cnt FROM `tabPermission Group Capability` GROUP BY parent",
        as_dict=True,
    )
    for c in caps:
        cap_counts[c["parent"]] = c["cnt"]

    # Build nodes
    nodes = {}
    for g in groups:
        nodes[g["name"]] = {
            "name": g["name"],
            "label": g.get("label") or g["name"],
            "parent_group": g.get("parent_group") or None,
            "member_count": member_counts.get(g["name"], 0),
            "capability_count": cap_counts.get(g["name"], 0),
            "children": [],
        }

    # Build tree
    roots = []
    for name, node in nodes.items():
        parent = node["parent_group"]
        if parent and parent in nodes:
            nodes[parent]["children"].append(node)
        else:
            roots.append(node)

    return roots


@frappe.whitelist()
def get_group_ancestors(group: str) -> list[str]:
    """
    Return ordered list of ancestor groups (parent, grandparent, ...)
    for a given Permission Group.

    Args:
        group: Permission Group name

    Returns:
        List of ancestor group names from immediate parent to root.
    """
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    if not frappe.db.exists("Permission Group", group):
        frappe.throw(f"Permission Group '{group}' not found")

    ancestors = []
    visited = {group}
    current = group

    while True:
        parent = frappe.db.get_value("Permission Group", current, "parent_group")
        if not parent or parent in visited:
            break
        ancestors.append(parent)
        visited.add(parent)
        current = parent

    return ancestors


@frappe.whitelist()
def get_group_descendants(group: str) -> list[str]:
    """
    Return flat list of all descendant groups (children, grandchildren, ...)
    for a given Permission Group. Uses BFS.

    Args:
        group: Permission Group name

    Returns:
        List of descendant group names.
    """
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    if not frappe.db.exists("Permission Group", group):
        frappe.throw(f"Permission Group '{group}' not found")

    all_groups = frappe.get_all(
        "Permission Group",
        fields=["name", "parent_group"],
    )

    # Build parent → children map
    children_map: dict[str, list[str]] = {}
    for g in all_groups:
        parent = g.get("parent_group")
        if parent:
            children_map.setdefault(parent, []).append(g["name"])

    # BFS
    descendants = []
    queue = children_map.get(group, [])[:]
    visited = {group}

    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        descendants.append(current)
        queue.extend(children_map.get(current, []))

    return descendants


@frappe.whitelist()
def get_effective_members(group: str, include_ancestors: bool = False) -> list[dict]:
    """
    Return members of a group, optionally including members inherited
    from ancestor groups (when hierarchy is enabled).

    Args:
        group: Permission Group name
        include_ancestors: if True, also include members from ancestor groups

    Returns:
        List of {user, group, is_direct, valid_from, valid_till}
    """
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    if isinstance(include_ancestors, str):
        include_ancestors = include_ancestors in ("true", "True", "1")

    if not frappe.db.exists("Permission Group", group):
        frappe.throw(f"Permission Group '{group}' not found")

    groups_to_check = [group]

    if include_ancestors:
        try:
            from caps.settings_helper import get_caps_settings
            if get_caps_settings().enable_group_hierarchy:
                ancestors = []
                visited = {group}
                current = group
                while True:
                    parent = frappe.db.get_value("Permission Group", current, "parent_group")
                    if not parent or parent in visited:
                        break
                    ancestors.append(parent)
                    visited.add(parent)
                    current = parent
                groups_to_check.extend(ancestors)
        except Exception:
            pass

    now = now_datetime()
    members = frappe.get_all(
        "Permission Group Member",
        filters={"parent": ("in", groups_to_check)},
        fields=["user", "parent as group_name", "valid_from", "valid_till"],
    )

    result = []
    seen_users = set()
    for m in members:
        # Skip expired/not-yet-started memberships
        if m.get("valid_from") and m["valid_from"] > now:
            continue
        if m.get("valid_till") and m["valid_till"] < now:
            continue

        user_key = f"{m['user']}:{m['group_name']}"
        if user_key in seen_users:
            continue
        seen_users.add(user_key)

        result.append({
            "user": m["user"],
            "group": m["group_name"],
            "is_direct": m["group_name"] == group,
            "valid_from": str(m["valid_from"]) if m.get("valid_from") else None,
            "valid_till": str(m["valid_till"]) if m.get("valid_till") else None,
        })

    return result


@frappe.whitelist()
def add_temp_member(group: str, user: str, valid_from: str = None, valid_till: str = None) -> dict:
    """
    Add a user to a Permission Group with optional temporary membership dates.

    Args:
        group: Permission Group name
        user: User email
        valid_from: Optional start datetime (ISO format). Blank = immediate.
        valid_till: Optional end datetime (ISO format). Blank = permanent.

    Returns:
        {success: True, member: {user, group, valid_from, valid_till}}
    """
    frappe.only_for(["CAPS Manager", "System Manager"])


    if not frappe.db.exists("Permission Group", group):
        frappe.throw(f"Permission Group '{group}' not found")
    if not frappe.db.exists("User", user):
        frappe.throw(f"User '{user}' not found")

    doc = frappe.get_doc("Permission Group", group)

    # Check if user is already a member
    for m in doc.members:
        if m.user == user:
            frappe.throw(f"User '{user}' is already a member of group '{group}'")

    row = doc.append("members", {
        "user": user,
        "added_by": frappe.session.user,
        "added_on": now_datetime(),
    })
    if valid_from:
        row.valid_from = valid_from
    if valid_till:
        row.valid_till = valid_till

    doc.save(ignore_permissions=True)

    return {
        "success": True,
        "member": {
            "user": user,
            "group": group,
            "valid_from": valid_from,
            "valid_till": valid_till,
        },
    }


@frappe.whitelist()
def get_effective_capabilities(group: str, include_ancestors: bool = False) -> list[dict]:
    """
    Return capabilities available to members of this group.
    If include_ancestors is True, also includes capabilities from ancestor groups.

    Args:
        group: Permission Group name
        include_ancestors: if True, traverse parent_group chain

    Returns:
        List of {capability, source_group, is_direct}
    """
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    if isinstance(include_ancestors, str):
        include_ancestors = include_ancestors in ("true", "True", "1")

    if not frappe.db.exists("Permission Group", group):
        frappe.throw(f"Permission Group '{group}' not found")

    groups_to_check = [group]

    if include_ancestors:
        try:
            from caps.settings_helper import get_caps_settings
            if get_caps_settings().enable_group_hierarchy:
                ancestors = []
                visited = {group}
                current = group
                while True:
                    parent = frappe.db.get_value("Permission Group", current, "parent_group")
                    if not parent or parent in visited:
                        break
                    ancestors.append(parent)
                    visited.add(parent)
                    current = parent
                groups_to_check.extend(ancestors)
        except Exception:
            pass

    # Direct capabilities
    caps_rows = frappe.get_all(
        "Permission Group Capability",
        filters={"parent": ("in", groups_to_check)},
        fields=["capability", "parent as source_group"],
    )

    result = []
    seen = set()
    for row in caps_rows:
        if row["capability"] not in seen:
            seen.add(row["capability"])
            result.append({
                "capability": row["capability"],
                "source_group": row["source_group"],
                "is_direct": row["source_group"] == group,
            })

    return result
