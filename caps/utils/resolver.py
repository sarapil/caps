# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS Resolution Engine
======================

Resolution Priority (highest to lowest):
1. Explicit DENY (reserved for future — always wins)
2. Direct User Capabilities (UserCapability doc)
3. Permission Group Capabilities (all groups user belongs to)
4. Role-based Capabilities (RoleCapabilityMap for user's Frappe roles)

Time-boxed capabilities are checked against current datetime.
Inactive capabilities are filtered out.
Results are cached in Redis with intelligent invalidation.
"""

import frappe
from frappe.utils import now_datetime

# Redis key prefixes
_CACHE_PREFIX = "caps:user:"
_CACHE_TTL = 300  # fallback default (overridden by CAPS Settings)
_FIELD_CACHE_PREFIX = "caps:fieldmap:"
_ACTION_CACHE_PREFIX = "caps:actionmap:"
_MAP_CACHE_TTL = 600  # fallback default (overridden by CAPS Settings)


def _get_cache_ttl():
    """Return user cache TTL from CAPS Settings (or fallback)."""
    try:
        from caps.settings_helper import get_caps_settings
        return get_caps_settings().cache_ttl
    except Exception:
        return _CACHE_TTL


def _get_map_cache_ttl():
    """Return field/action map cache TTL from CAPS Settings (or fallback)."""
    try:
        from caps.settings_helper import get_caps_settings
        return get_caps_settings().field_map_cache_ttl
    except Exception:
        return _MAP_CACHE_TTL


def _is_caps_enabled():
    """Check if CAPS enforcement is globally enabled."""
    try:
        from caps.settings_helper import get_caps_settings
        return get_caps_settings().enable_caps
    except Exception:
        return True


def _admin_bypass_enabled():
    """Check if Administrator bypass is enabled."""
    try:
        from caps.settings_helper import get_caps_settings
        return get_caps_settings().admin_bypass
    except Exception:
        return True


def _guest_empty_set_enabled():
    """Check if Guest empty set is enabled."""
    try:
        from caps.settings_helper import get_caps_settings
        return get_caps_settings().guest_empty_set
    except Exception:
        return True


# ─── Primary Resolution ──────────────────────────────────────────────


def resolve_capabilities(user: str | None = None) -> set[str]:
    """
    Return the COMPLETE set of active capability names for a user.

    Algorithm:
    1. Administrator → ALL active capabilities
    2. Redis cache → return if valid
    3. Collect from 3 channels (direct, groups, roles)
    4. Filter inactive + expired
    5. Cache in Redis (TTL 300s)
    """
    user = user or frappe.session.user

    # Global kill-switch: when CAPS is disabled, everyone gets all capabilities
    if not _is_caps_enabled():
        return _all_active_capabilities()

    if user == "Administrator" and _admin_bypass_enabled():
        return _all_active_capabilities()

    if user == "Guest" and _guest_empty_set_enabled():
        return set()

    # Impersonation: if CAPS Admin is impersonating, resolve the target's caps
    if user == frappe.session.user:
        try:
            from caps.api_impersonation import get_impersonation_state
            imp = get_impersonation_state(user)
            if imp:
                return resolve_capabilities(imp["target_user"])
        except Exception:
            pass

    # Check cache
    cached = frappe.cache.get_value(f"{_CACHE_PREFIX}{user}")
    if cached is not None:
        return set(cached)

    caps: set[str] = set()
    now = now_datetime()
    active_caps = _all_active_capability_names()

    # Channel 1: Direct user capabilities
    caps |= _collect_direct_user(user, now, active_caps)

    # Channel 2: Permission groups the user belongs to
    caps |= _collect_from_groups(user, active_caps)

    # Channel 3: Role-based capabilities
    caps |= _collect_from_roles(user, active_caps)

    # Channel 4: Hierarchy inheritance — expand children of held capabilities
    caps = _expand_hierarchy(caps, active_caps)

    # Enforce hard prerequisites: remove caps whose prereqs are not met
    caps = _enforce_prerequisites(caps)

    # Cache with dynamic TTL from settings
    frappe.cache.set_value(f"{_CACHE_PREFIX}{user}", list(caps), expires_in_sec=_get_cache_ttl())
    return caps


# ─── Public Helpers ──────────────────────────────────────────────────


def has_capability(capability: str, user: str | None = None) -> bool:
    """Check if user has a single capability."""
    user = user or frappe.session.user
    return capability in resolve_capabilities(user)


def has_any_capability(*capabilities: str, user: str | None = None) -> bool:
    """True if user has ANY of the listed capabilities."""
    user = user or frappe.session.user
    user_caps = resolve_capabilities(user)
    return bool(user_caps & set(capabilities))


def has_all_capabilities(*capabilities: str, user: str | None = None) -> bool:
    """True if user has ALL listed capabilities."""
    user = user or frappe.session.user
    user_caps = resolve_capabilities(user)
    return set(capabilities).issubset(user_caps)


def require_capability(capability: str, user: str | None = None):
    """Raise frappe.PermissionError if capability is missing. Use as guard."""
    user = user or frappe.session.user
    if not has_capability(capability, user):
        _audit_denied(user, capability)
        frappe.throw(
            f"Missing capability: {capability}",
            frappe.PermissionError,
        )


# ─── Field & Action Restrictions ─────────────────────────────────────


def get_field_restrictions(doctype: str, user: str | None = None) -> dict:
    """
    Return {fieldname: {behavior, mask_pattern, custom_handler, priority}}
    for all fields the user CANNOT access on this doctype.
    """
    user = user or frappe.session.user
    if user == "Administrator":
        return {}

    user_caps = resolve_capabilities(user)
    field_maps = _get_field_maps(doctype)

    restrictions = {}
    for fm in field_maps:
        if fm["capability"] not in user_caps:
            fn = fm["fieldname"]
            # Higher priority wins on conflict
            if fn not in restrictions or fm["priority"] > restrictions[fn].get("priority", 0):
                restrictions[fn] = {
                    "behavior": fm["behavior"],
                    "mask_pattern": fm.get("mask_pattern") or "",
                    "custom_handler": fm.get("custom_handler") or "",
                    "priority": fm.get("priority") or 0,
                }
    return restrictions


def get_action_restrictions(doctype: str, user: str | None = None) -> list[dict]:
    """
    Return list of {action_id, action_type, fallback_behavior, fallback_message}
    for actions the user CANNOT perform on this doctype.
    """
    user = user or frappe.session.user
    if user == "Administrator":
        return []

    user_caps = resolve_capabilities(user)
    action_maps = _get_action_maps(doctype)

    restrictions = []
    for am in action_maps:
        if am["capability"] not in user_caps:
            restrictions.append({
                "action_id": am["action_id"],
                "action_type": am["action_type"],
                "fallback_behavior": am["fallback_behavior"],
                "fallback_message": am.get("fallback_message") or "",
            })
    return restrictions


def get_field_restrictions_all(user: str | None = None) -> dict:
    """
    Return {doctype: {fieldname: {behavior, ...}}} for ALL doctypes
    that have Field Capability Maps. Used by boot_session.
    """
    user = user or frappe.session.user
    if user == "Administrator":
        return {}

    user_caps = resolve_capabilities(user)

    all_maps = frappe.get_all(
        "Field Capability Map",
        fields=["doctype_name", "fieldname", "capability", "behavior",
                "mask_pattern", "custom_handler", "priority"],
    )

    result: dict = {}
    for fm in all_maps:
        if fm["capability"] not in user_caps:
            dt = fm["doctype_name"]
            fn = fm["fieldname"]
            if dt not in result:
                result[dt] = {}
            existing = result[dt].get(fn)
            if not existing or (fm.get("priority") or 0) > existing.get("priority", 0):
                result[dt][fn] = {
                    "behavior": fm["behavior"],
                    "mask_pattern": fm.get("mask_pattern") or "",
                    "custom_handler": fm.get("custom_handler") or "",
                    "priority": fm.get("priority") or 0,
                }
    return result


def get_action_restrictions_all(user: str | None = None) -> dict:
    """
    Return {doctype: [{action_id, action_type, ...}]} for ALL doctypes
    that have Action Capability Maps. Used by boot_session.
    """
    user = user or frappe.session.user
    if user == "Administrator":
        return {}

    user_caps = resolve_capabilities(user)

    all_maps = frappe.get_all(
        "Action Capability Map",
        fields=["doctype_name", "action_id", "action_type",
                "capability", "fallback_behavior", "fallback_message"],
    )

    result: dict = {}
    for am in all_maps:
        if am["capability"] not in user_caps:
            dt = am["doctype_name"]
            if dt not in result:
                result[dt] = []
            result[dt].append({
                "action_id": am["action_id"],
                "action_type": am["action_type"],
                "fallback_behavior": am["fallback_behavior"],
                "fallback_message": am.get("fallback_message") or "",
            })
    return result


# ─── Cache Invalidation ──────────────────────────────────────────────


def invalidate_user_cache(user: str):
    """Clear cached capabilities for a specific user."""
    frappe.cache.delete_value(f"{_CACHE_PREFIX}{user}")


def invalidate_all_caches():
    """Clear ALL cached capabilities (use sparingly)."""
    frappe.cache.delete_keys(f"{_CACHE_PREFIX}*")


def invalidate_field_action_caches():
    """Bump the map version so clients re-fetch restrictions."""
    version = int(frappe.cache.get_value("caps:map_version") or 0)
    frappe.cache.set_value("caps:map_version", version + 1)
    # Clear server-side field/action map caches
    for prefix in (_FIELD_CACHE_PREFIX, _ACTION_CACHE_PREFIX):
        frappe.cache.delete_keys(f"{prefix}*")
    # Also clear prerequisite map cache
    frappe.cache.delete_value("caps:prereq_map")


# ─── Internals ────────────────────────────────────────────────────────


def _all_active_capabilities() -> set[str]:
    """Return ALL active capability names (for Administrator)."""
    return set(
        frappe.get_all("Capability", filters={"is_active": 1}, pluck="name")
    )


def _all_active_capability_names() -> set[str]:
    """Return set of active capability names for filtering."""
    return _all_active_capabilities()


def _expand_bundles(bundle_names: list[str], active_caps: set[str]) -> set[str]:
    """Given a list of bundle names, expand to individual capability names."""
    if not bundle_names:
        return set()

    caps = set()
    items = frappe.get_all(
        "Capability Bundle Item",
        filters={"parent": ("in", bundle_names)},
        fields=["capability"],
    )
    for item in items:
        if item["capability"] in active_caps:
            caps.add(item["capability"])
    return caps


def _collect_direct_user(user: str, now, active_caps: set[str]) -> set[str]:
    """Channel 1: Capabilities assigned directly to the user."""
    caps = set()
    if not frappe.db.exists("User Capability", user):
        return caps

    doc = frappe.get_doc("User Capability", user)

    # Direct capabilities
    for row in doc.direct_capabilities:
        if row.expires_on and row.expires_on < now:
            continue
        if row.capability in active_caps:
            caps.add(row.capability)

    # Expand bundles
    bundle_names = []
    for row in doc.direct_bundles:
        if row.expires_on and row.expires_on < now:
            continue
        bundle_names.append(row.bundle)

    caps |= _expand_bundles(bundle_names, active_caps)
    return caps


def _collect_from_groups(user: str, active_caps: set[str]) -> set[str]:
    """Channel 2: Capabilities from Permission Groups the user belongs to.

    If group hierarchy is enabled, also collects capabilities from
    ancestor groups (parent_group chain).
    """
    caps = set()
    now = now_datetime()

    # Find all groups where user is a member (filtering expired memberships)
    memberships = frappe.get_all(
        "Permission Group Member",
        filters={"user": user},
        fields=["parent", "valid_from", "valid_till"],
    )

    group_names = []
    for m in memberships:
        # Skip if membership hasn't started yet
        if m.get("valid_from") and m["valid_from"] > now:
            continue
        # Skip if membership has expired
        if m.get("valid_till") and m["valid_till"] < now:
            continue
        group_names.append(m["parent"])

    if not group_names:
        return caps

    # If group hierarchy is enabled, expand to include ancestor groups
    if _is_group_hierarchy_enabled():
        group_names = _expand_group_ancestors(group_names)

    # Direct capabilities from groups
    group_caps = frappe.get_all(
        "Permission Group Capability",
        filters={"parent": ("in", group_names)},
        pluck="capability",
    )
    for c in group_caps:
        if c in active_caps:
            caps.add(c)

    # Bundles from groups
    group_bundles = frappe.get_all(
        "Permission Group Bundle",
        filters={"parent": ("in", group_names)},
        pluck="bundle",
    )
    caps |= _expand_bundles(group_bundles, active_caps)

    return caps


def _collect_from_roles(user: str, active_caps: set[str]) -> set[str]:
    """Channel 3: Capabilities via RoleCapabilityMap for the user's Frappe roles."""
    caps = set()

    user_roles = frappe.get_roles(user)
    if not user_roles:
        return caps

    # Find Role Capability Maps for user's roles
    role_maps = frappe.get_all(
        "Role Capability Map",
        filters={"role": ("in", user_roles)},
        pluck="name",
    )

    if not role_maps:
        return caps

    # Direct capabilities from role maps
    role_caps = frappe.get_all(
        "Role Capability Item",
        filters={"parent": ("in", role_maps)},
        pluck="capability",
    )
    for c in role_caps:
        if c in active_caps:
            caps.add(c)

    # Bundles from role maps
    role_bundles = frappe.get_all(
        "Role Capability Bundle",
        filters={"parent": ("in", role_maps)},
        pluck="bundle",
    )
    caps |= _expand_bundles(role_bundles, active_caps)

    return caps


def _get_field_maps(doctype: str) -> list[dict]:
    """Get all Field Capability Maps for a doctype (cached)."""
    cache_key = f"{_FIELD_CACHE_PREFIX}{doctype}"
    cached = frappe.cache.get_value(cache_key)
    if cached is not None:
        return cached

    maps = frappe.get_all(
        "Field Capability Map",
        filters={"doctype_name": doctype},
        fields=["fieldname", "capability", "behavior", "mask_pattern",
                "custom_handler", "priority"],
    )
    frappe.cache.set_value(cache_key, maps, expires_in_sec=_get_map_cache_ttl())
    return maps


def _get_action_maps(doctype: str) -> list[dict]:
    """Get all Action Capability Maps for a doctype (cached)."""
    cache_key = f"{_ACTION_CACHE_PREFIX}{doctype}"
    cached = frappe.cache.get_value(cache_key)
    if cached is not None:
        return cached

    maps = frappe.get_all(
        "Action Capability Map",
        filters={"doctype_name": doctype},
        fields=["action_id", "action_type", "capability",
                "fallback_behavior", "fallback_message"],
    )
    frappe.cache.set_value(cache_key, maps, expires_in_sec=_get_map_cache_ttl())
    return maps


def _is_audit_logging_enabled():
    """Check if audit logging is enabled."""
    try:
        from caps.settings_helper import get_caps_settings
        return get_caps_settings().enable_audit_logging
    except Exception:
        return True


def _is_group_hierarchy_enabled():
    """Check if group hierarchy traversal is enabled."""
    try:
        from caps.settings_helper import get_caps_settings
        return get_caps_settings().enable_group_hierarchy
    except Exception:
        return True


def _expand_group_ancestors(group_names: list[str]) -> list[str]:
    """Expand a list of groups to include all ancestor groups via parent_group chain.

    Uses BFS traversal to walk up the parent_group hierarchy. This allows
    a user who is a member of a child group to inherit capabilities from
    all ancestor groups.

    Cached with the group hierarchy map.
    """
    hierarchy_map = _get_group_hierarchy_map()
    expanded = set(group_names)
    queue = list(group_names)

    while queue:
        current = queue.pop(0)
        parent = hierarchy_map.get(current)
        if parent and parent not in expanded:
            expanded.add(parent)
            queue.append(parent)

    return list(expanded)


def _get_group_hierarchy_map() -> dict[str, str | None]:
    """Return {group_name: parent_group_name} map for all groups. Cached.

    Returns a dict mapping each Permission Group name to its parent group
    name (or None if it has no parent).
    """
    cache_key = "caps:group_hierarchy_map"
    cached = frappe.cache.get_value(cache_key)
    if cached is not None:
        return cached

    groups = frappe.get_all(
        "Permission Group",
        fields=["name", "parent_group"],
    )
    hierarchy = {}
    for g in groups:
        hierarchy[g["name"]] = g.get("parent_group") or None

    frappe.cache.set_value(cache_key, hierarchy, expires_in_sec=_get_map_cache_ttl())
    return hierarchy


def _get_prerequisite_map() -> dict[str, list[str]]:
    """
    Return {capability_name: [hard_prerequisite_names]} for ALL capabilities
    that have hard prerequisites. Cached with map TTL.
    """
    cache_key = "caps:prereq_map"
    cached = frappe.cache.get_value(cache_key)
    if cached is not None:
        return cached

    rows = frappe.get_all(
        "Capability Prerequisite",
        filters={"parenttype": "Capability", "is_hard": 1},
        fields=["parent", "prerequisite"],
    )

    prereq_map: dict[str, list[str]] = {}
    for row in rows:
        prereq_map.setdefault(row["parent"], []).append(row["prerequisite"])

    frappe.cache.set_value(cache_key, prereq_map, expires_in_sec=_get_map_cache_ttl())
    return prereq_map


def _get_hierarchy_map() -> dict[str, list[str]]:
    """
    Return {parent_capability: [child1, child2, ...]} for all capabilities
    with a parent_capability set.  Cached in Redis.
    """
    cache_key = "caps:hierarchy_map"
    cached = frappe.cache.get_value(cache_key)
    if cached is not None:
        return cached

    rows = frappe.get_all(
        "Capability",
        filters={"parent_capability": ("is", "set"), "is_active": 1},
        fields=["name", "parent_capability"],
    )

    hierarchy: dict[str, list[str]] = {}
    for row in rows:
        hierarchy.setdefault(row["parent_capability"], []).append(row["name"])

    frappe.cache.set_value(cache_key, hierarchy, expires_in_sec=_get_map_cache_ttl())
    return hierarchy


def _expand_hierarchy(caps: set[str], active_caps: set[str]) -> set[str]:
    """
    Expand capabilities by adding children of held parent capabilities.

    If a user has capability "crm:all", and "crm:read" and "crm:write" have
    parent_capability="crm:all", the user automatically gets those children.

    Handles multi-level hierarchies iteratively.
    """
    hierarchy = _get_hierarchy_map()
    if not hierarchy:
        return caps

    expanded = set(caps)
    frontier = set(caps)

    while frontier:
        new_children = set()
        for cap in frontier:
            children = hierarchy.get(cap, [])
            for child in children:
                if child not in expanded and child in active_caps:
                    new_children.add(child)
        if not new_children:
            break
        expanded |= new_children
        frontier = new_children  # Recurse into newly added children

    return expanded


def _enforce_prerequisites(caps: set[str]) -> set[str]:
    """
    Remove capabilities whose hard prerequisites are not in the set.

    Iterates until stable (handles transitive deps where removing A
    may cause B to lose its prereq).
    """
    prereq_map = _get_prerequisite_map()
    if not prereq_map:
        return caps

    changed = True
    while changed:
        changed = False
        to_remove = set()
        for cap in caps:
            prereqs = prereq_map.get(cap)
            if prereqs and not all(p in caps for p in prereqs):
                to_remove.add(cap)
        if to_remove:
            caps -= to_remove
            changed = True

    return caps


def get_dependency_graph(capability: str | None = None) -> dict:
    """
    Return the dependency graph for a single capability or ALL capabilities.

    Returns:
        {
            "nodes": [{"name": str, "label": str, "is_active": bool}],
            "edges": [{"from": str, "to": str, "is_hard": bool}],
        }
    """
    if capability:
        # Single capability and its transitive dependencies
        return _single_dep_graph(capability)

    # Full graph
    all_prereqs = frappe.get_all(
        "Capability Prerequisite",
        filters={"parenttype": "Capability"},
        fields=["parent", "prerequisite", "is_hard"],
    )

    involved = set()
    edges = []
    for row in all_prereqs:
        involved.add(row["parent"])
        involved.add(row["prerequisite"])
        edges.append({
            "from": row["parent"],
            "to": row["prerequisite"],
            "is_hard": bool(row["is_hard"]),
        })

    nodes = []
    if involved:
        caps = frappe.get_all(
            "Capability",
            filters={"name": ("in", list(involved))},
            fields=["name", "label", "is_active"],
        )
        nodes = [{"name": c["name"], "label": c["label"], "is_active": bool(c["is_active"])} for c in caps]

    return {"nodes": nodes, "edges": edges}


def _single_dep_graph(capability: str) -> dict:
    """Build transitive dep graph for one capability via BFS."""
    visited = set()
    queue = [capability]
    edges = []

    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)

        prereqs = frappe.get_all(
            "Capability Prerequisite",
            filters={"parent": current, "parenttype": "Capability"},
            fields=["prerequisite", "is_hard"],
        )
        for p in prereqs:
            edges.append({
                "from": current,
                "to": p["prerequisite"],
                "is_hard": bool(p["is_hard"]),
            })
            if p["prerequisite"] not in visited:
                queue.append(p["prerequisite"])

    nodes = []
    if visited:
        caps = frappe.get_all(
            "Capability",
            filters={"name": ("in", list(visited))},
            fields=["name", "label", "is_active"],
        )
        nodes = [{"name": c["name"], "label": c["label"], "is_active": bool(c["is_active"])} for c in caps]

    return {"nodes": nodes, "edges": edges}



def _audit_denied(user: str, capability: str):
    """Log a denied capability check to the audit log."""
    if not _is_audit_logging_enabled():
        return
    try:
        frappe.get_doc({
            "doctype": "CAPS Audit Log",
            "user": user,
            "action": "capability_check",
            "capability": capability,
            "result": "denied",
            "timestamp": now_datetime(),
            "ip_address": frappe.local.request_ip if hasattr(frappe.local, "request_ip") else "",
        }).insert(ignore_permissions=True)
    except Exception:
        # Never let audit logging break the flow
        pass
