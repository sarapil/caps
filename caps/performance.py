# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS – Performance Optimization Engine
========================================

Optimized resolution and caching strategies for large-scale deployments:

1. **Lazy Resolution** — Resolve only the capabilities actually checked,
   deferring full resolution until needed.

2. **Differential Cache Updates** — Update cache by applying deltas
   (additions/removals) instead of full recalculation.

3. **Query Optimization** — Batch DB queries and use optimized SQL
   for large user bases.

4. **Cache Warming** — Pre-populate caches on startup for active users
   and frequently accessed data.

5. **Batch Resolution** — Resolve capabilities for multiple users in
   a single optimized pass.
"""

import frappe
from frappe.utils import now_datetime

# ─── Lazy Resolution ─────────────────────────────────────────────────


def lazy_has_capability(capability: str, user: str | None = None) -> bool:
    """
    Check a single capability without resolving the full set.

    Optimized path: checks Redis cache first, then DB channels
    only until the capability is found (short-circuit).

    Falls back to full resolution if no shortcut found.
    """
    user = user or frappe.session.user

    # Check full cache first (might already be resolved)
    from caps.utils.resolver import _CACHE_PREFIX
    cached = frappe.cache.get_value(f"{_CACHE_PREFIX}{user}")
    if cached is not None:
        return capability in set(cached)

    # Check single-cap cache
    single_key = f"caps:single:{user}:{capability}"
    single_cached = frappe.cache.get_value(single_key)
    if single_cached is not None:
        return single_cached == "1"

    # Quick DB checks (short-circuit)
    found = _quick_check_direct(capability, user)
    if found is None:
        found = _quick_check_groups(capability, user)
    if found is None:
        found = _quick_check_roles(capability, user)

    if found is not None:
        frappe.cache.set_value(single_key, "1" if found else "0", expires_in_sec=60)
        return found

    # Fallback to full resolution
    from caps.utils.resolver import has_capability
    return has_capability(capability, user)


def _quick_check_direct(capability: str, user: str) -> bool | None:
    """Quick check: does user have this capability directly?"""
    if not frappe.db.exists("User Capability", user):
        return None

    now = now_datetime()
    result = frappe.db.sql("""
        SELECT 1 FROM `tabUser Capability Item`
        WHERE parent = %s AND capability = %s
        AND (expires_on IS NULL OR expires_on > %s)
        LIMIT 1
    """, (user, capability, now))

    if result:
        return True
    return None  # Not found directly, try other channels


def _quick_check_groups(capability: str, user: str) -> bool | None:
    """Quick check: does any of user's groups have this capability?"""
    now = now_datetime()
    result = frappe.db.sql("""
        SELECT 1
        FROM `tabPermission Group Member` pgm
        INNER JOIN `tabPermission Group Capability` pgc
            ON pgm.parent = pgc.parent
        WHERE pgm.user = %s AND pgc.capability = %s
        AND (pgm.valid_from IS NULL OR pgm.valid_from <= %s)
        AND (pgm.valid_till IS NULL OR pgm.valid_till > %s)
        LIMIT 1
    """, (user, capability, now, now))

    if result:
        return True
    return None


def _quick_check_roles(capability: str, user: str) -> bool | None:
    """Quick check: does any of user's roles grant this capability?"""
    result = frappe.db.sql("""
        SELECT 1
        FROM `tabHas Role` hr
        INNER JOIN `tabRole Capability Item` rci
            ON hr.role = rci.parent
        WHERE hr.parent = %s AND hr.parenttype = 'User'
        AND rci.capability = %s
        LIMIT 1
    """, (user, capability))

    if result:
        return True
    return None


# ─── Differential Cache Updates ──────────────────────────────────────


def apply_cache_delta(user: str, added: list[str] | None = None,
                      removed: list[str] | None = None):
    """
    Apply a delta to a user's cached capabilities.

    Instead of recalculating the entire set, just add/remove
    specific capabilities from the cached set.

    If no cache exists, falls back to full resolution.
    """
    from caps.utils.resolver import _CACHE_PREFIX, _get_cache_ttl

    cache_key = f"{_CACHE_PREFIX}{user}"
    cached = frappe.cache.get_value(cache_key)

    if cached is None:
        # No cache to update, will be rebuilt on next access
        return

    caps = set(cached)

    if added:
        caps |= set(added)
    if removed:
        caps -= set(removed)

    frappe.cache.set_value(cache_key, list(caps), expires_in_sec=_get_cache_ttl())


# ─── Batch Resolution ────────────────────────────────────────────────


def batch_resolve(users: list[str]) -> dict[str, set[str]]:
    """
    Resolve capabilities for multiple users in an optimized batch.

    Shares DB queries across users where possible.

    Returns: {user_email: set_of_capabilities}
    """
    from caps.utils.resolver import (
        _CACHE_PREFIX, _get_cache_ttl, _all_active_capability_names,
        _expand_bundles, _expand_hierarchy, _enforce_prerequisites,
    )

    active_caps = _all_active_capability_names()
    now = now_datetime()
    results = {}
    uncached_users = []

    # Check cache first
    for user in users:
        cached = frappe.cache.get_value(f"{_CACHE_PREFIX}{user}")
        if cached is not None:
            results[user] = set(cached)
        else:
            uncached_users.append(user)

    if not uncached_users:
        return results

    # Batch fetch: direct capabilities
    direct_caps = _batch_fetch_direct(uncached_users, now, active_caps)

    # Batch fetch: group capabilities
    group_caps = _batch_fetch_groups(uncached_users, active_caps)

    # Batch fetch: role capabilities
    role_caps = _batch_fetch_roles(uncached_users, active_caps)

    # Merge channels per user
    for user in uncached_users:
        user_caps = set()
        user_caps |= direct_caps.get(user, set())
        user_caps |= group_caps.get(user, set())
        user_caps |= role_caps.get(user, set())

        # Expand hierarchy and enforce prerequisites
        user_caps = _expand_hierarchy(user_caps, active_caps)
        user_caps = _enforce_prerequisites(user_caps)

        # Cache
        frappe.cache.set_value(
            f"{_CACHE_PREFIX}{user}", list(user_caps),
            expires_in_sec=_get_cache_ttl(),
        )
        results[user] = user_caps

    return results


def _batch_fetch_direct(users: list[str], now, active_caps: set[str]) -> dict[str, set[str]]:
    """Batch fetch direct capabilities for multiple users."""
    result: dict[str, set[str]] = {u: set() for u in users}

    placeholders = ", ".join(["%s"] * len(users))
    rows = frappe.db.sql(f"""
        SELECT parent, capability, expires_on
        FROM `tabUser Capability Item`
        WHERE parent IN ({placeholders})
    """, users, as_dict=True)

    for row in rows:
        if row["expires_on"] and row["expires_on"] < now:
            continue
        if row["capability"] in active_caps:
            result[row["parent"]].add(row["capability"])

    # Also fetch bundles
    bundle_rows = frappe.db.sql(f"""
        SELECT parent, bundle, expires_on
        FROM `tabUser Capability Bundle`
        WHERE parent IN ({placeholders})
    """, users, as_dict=True)

    user_bundles: dict[str, list[str]] = {}
    for row in bundle_rows:
        if row["expires_on"] and row["expires_on"] < now:
            continue
        user_bundles.setdefault(row["parent"], []).append(row["bundle"])

    # Expand all bundles at once
    all_bundles = set()
    for bundles in user_bundles.values():
        all_bundles.update(bundles)

    if all_bundles:
        from caps.utils.resolver import _expand_bundles
        expanded = _expand_bundles(list(all_bundles), active_caps)
        for user, bundles in user_bundles.items():
            # Each user gets caps from their bundles
            user_bundle_caps = _expand_bundles(bundles, active_caps)
            result[user] |= user_bundle_caps

    return result


def _batch_fetch_groups(users: list[str], active_caps: set[str]) -> dict[str, set[str]]:
    """Batch fetch group capabilities for multiple users."""
    result: dict[str, set[str]] = {u: set() for u in users}

    now = now_datetime()
    placeholders = ", ".join(["%s"] * len(users))
    rows = frappe.db.sql(f"""
        SELECT pgm.user, pgc.capability
        FROM `tabPermission Group Member` pgm
        INNER JOIN `tabPermission Group Capability` pgc
            ON pgm.parent = pgc.parent
        WHERE pgm.user IN ({placeholders})
        AND (pgm.valid_from IS NULL OR pgm.valid_from <= %s)
        AND (pgm.valid_till IS NULL OR pgm.valid_till > %s)
    """, (*users, now, now), as_dict=True)

    for row in rows:
        if row["capability"] in active_caps:
            result[row["user"]].add(row["capability"])

    return result


def _batch_fetch_roles(users: list[str], active_caps: set[str]) -> dict[str, set[str]]:
    """Batch fetch role capabilities for multiple users."""
    result: dict[str, set[str]] = {u: set() for u in users}

    placeholders = ", ".join(["%s"] * len(users))
    rows = frappe.db.sql(f"""
        SELECT hr.parent as user, rci.capability
        FROM `tabHas Role` hr
        INNER JOIN `tabRole Capability Item` rci
            ON hr.role = rci.parent
        WHERE hr.parent IN ({placeholders})
        AND hr.parenttype = 'User'
    """, users, as_dict=True)

    for row in rows:
        if row["capability"] in active_caps:
            result[row["user"]].add(row["capability"])

    return result


# ─── Cache Warming ───────────────────────────────────────────────────


def warm_caches(max_users: int = 100):
    """
    Pre-populate capability caches for active users.

    Called on startup or on demand to reduce cold-cache latency.
    Warms caches for the most recently active users.
    """
    # Get most recently active users
    active_users = frappe.db.sql("""
        SELECT name FROM `tabUser`
        WHERE enabled = 1 AND name NOT IN ('Guest', 'Administrator')
        ORDER BY last_active DESC
        LIMIT %s
    """, (max_users,), as_dict=True)

    users = [u["name"] for u in active_users]
    if not users:
        return {"warmed": 0}

    results = batch_resolve(users)
    return {"warmed": len(results)}


def warm_map_caches():
    """
    Pre-populate field/action map caches for all doctypes that have maps.

    Eliminates cold-cache latency for the first form load.
    """
    from caps.utils.resolver import _get_field_maps, _get_action_maps

    # Get all doctypes with field maps
    field_doctypes = frappe.get_all(
        "Field Capability Map",
        pluck="doctype_name",
        distinct=True,
    )
    for dt in field_doctypes:
        _get_field_maps(dt)

    # Get all doctypes with action maps
    action_doctypes = frappe.get_all(
        "Action Capability Map",
        pluck="doctype_name",
        distinct=True,
    )
    for dt in action_doctypes:
        _get_action_maps(dt)

    return {
        "field_map_doctypes": len(field_doctypes),
        "action_map_doctypes": len(action_doctypes),
    }
