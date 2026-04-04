# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS Cache Invalidation
=======================

Handles intelligent cache invalidation via doc_events configured in hooks.py.

Event                           → Invalidation
────────────────────────────────────────────────
UserCapability saved            → That user's cache
Permission Group saved          → All group members' caches
Capability Bundle saved         → All users referencing the bundle
Role Capability Map saved       → All users with that role
Field/Action Capability Map     → Client-side version bump
"""

import frappe


def on_capability_change(doc, method=None):
    """Capability created/updated/deleted → invalidate prereq map + hierarchy + all user caches."""
    from caps.utils.resolver import invalidate_all_caches
    # Prereq map is cleared inside invalidate_field_action_caches (called by all_caches too)
    frappe.cache.delete_value("caps:prereq_map")
    frappe.cache.delete_value("caps:hierarchy_map")
    frappe.cache.delete_value("caps:group_hierarchy_map")
    invalidate_all_caches()


def on_user_capability_change(doc, method=None):
    """UserCapability created/updated/deleted → invalidate that user's cache."""
    from caps.utils.resolver import invalidate_user_cache
    user = doc.user if hasattr(doc, "user") else doc.name
    invalidate_user_cache(user)


def on_permission_group_change(doc, method=None):
    """Permission Group changed → invalidate ALL group members' caches.

    When group hierarchy is enabled, also cascades to members of all
    descendant (child) groups, since changing a parent group's capabilities
    affects what child group members inherit.

    Also clears the group hierarchy map cache.
    """
    from caps.utils.resolver import invalidate_user_cache

    # Always clear the group hierarchy map cache
    frappe.cache.delete_value("caps:group_hierarchy_map")

    # Collect all users to invalidate (direct members)
    users_to_invalidate = set()
    for row in doc.members:
        users_to_invalidate.add(row.user)

    # If hierarchy enabled, find all descendant groups and their members
    try:
        from caps.settings_helper import get_caps_settings
        hierarchy_enabled = get_caps_settings().enable_group_hierarchy
    except Exception:
        hierarchy_enabled = True

    if hierarchy_enabled:
        child_groups = _get_all_descendant_groups(doc.name)
        if child_groups:
            child_members = frappe.get_all(
                "Permission Group Member",
                filters={"parent": ("in", child_groups)},
                pluck="user",
            )
            for u in child_members:
                users_to_invalidate.add(u)

    for u in users_to_invalidate:
        invalidate_user_cache(u)


def _get_all_descendant_groups(group_name: str) -> list[str]:
    """BFS to find all descendant groups (children, grandchildren, etc.)."""
    all_children = frappe.get_all(
        "Permission Group",
        fields=["name", "parent_group"],
    )
    # Build parent → children map
    children_map: dict[str, list[str]] = {}
    for g in all_children:
        parent = g.get("parent_group")
        if parent:
            children_map.setdefault(parent, []).append(g["name"])

    # BFS from group_name
    descendants = []
    queue = children_map.get(group_name, [])[:]
    visited = {group_name}
    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        descendants.append(current)
        queue.extend(children_map.get(current, []))

    return descendants


def on_bundle_change(doc, method=None):
    """Capability Bundle changed → invalidate users referencing this bundle."""
    from caps.utils.resolver import invalidate_user_cache

    bundle_name = doc.name

    # Users with this bundle directly
    users = frappe.get_all(
        "User Capability Bundle",
        filters={"bundle": bundle_name},
        pluck="parent",
    )
    for u in users:
        invalidate_user_cache(u)

    # Groups with this bundle → all their members
    groups = frappe.get_all(
        "Permission Group Bundle",
        filters={"bundle": bundle_name},
        pluck="parent",
    )
    if groups:
        members = frappe.get_all(
            "Permission Group Member",
            filters={"parent": ("in", groups)},
            pluck="user",
        )
        for u in members:
            invalidate_user_cache(u)

    # Role maps with this bundle → all users with those roles
    role_maps = frappe.get_all(
        "Role Capability Bundle",
        filters={"bundle": bundle_name},
        pluck="parent",
    )
    if role_maps:
        for role_name in role_maps:
            users_with_role = frappe.get_all(
                "Has Role",
                filters={"role": role_name, "parenttype": "User"},
                pluck="parent",
            )
            for u in users_with_role:
                invalidate_user_cache(u)


def on_role_map_change(doc, method=None):
    """Role Capability Map changed → invalidate all users with that role."""
    from caps.utils.resolver import invalidate_user_cache

    role = doc.role if hasattr(doc, "role") else doc.name
    users_with_role = frappe.get_all(
        "Has Role",
        filters={"role": role, "parenttype": "User"},
        pluck="parent",
    )
    for u in users_with_role:
        invalidate_user_cache(u)


def on_field_map_change(doc, method=None):
    """Field Capability Map changed → bump client-side version."""
    from caps.utils.resolver import invalidate_field_action_caches
    invalidate_field_action_caches()


def on_action_map_change(doc, method=None):
    """Action Capability Map changed → bump client-side version."""
    from caps.utils.resolver import invalidate_field_action_caches
    invalidate_field_action_caches()


def on_rate_limit_change(doc, method=None):
    """Capability Rate Limit changed → clear rate rule cache."""
    frappe.cache.delete_value("caps:rate_rules")
