# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS – Rate Limiter Engine
============================

Redis-based sliding-window rate limiter for capability usage.

Each Capability Rate Limit doc defines per-hour/day/week/month quotas.
Usage is tracked via Redis sorted sets with timestamps as scores,
giving accurate sliding-window semantics with automatic expiry.

Usage:
    from caps.rate_limiter import check_rate_limit, record_usage

    result = check_rate_limit("export:data", "user@example.com")
    if not result["allowed"]:
        frappe.throw(result["message"])

    # After successful action:
    record_usage("export:data", "user@example.com")
"""

import frappe
from frappe.utils import now_datetime
import time


# Redis key prefix
_RATE_PREFIX = "caps:rate:"

# Window durations in seconds
_WINDOWS = {
    "hour": 3600,
    "day": 86400,
    "week": 604800,
    "month": 2592000,  # 30 days
}

# Map window names to DocType fields
_LIMIT_FIELDS = {
    "hour": "max_per_hour",
    "day": "max_per_day",
    "week": "max_per_week",
    "month": "max_per_month",
}


def check_rate_limit(capability: str, user: str | None = None) -> dict:
    """
    Check if a capability usage is within rate limits.

    Returns:
        {
            "allowed": bool,
            "capability": str,
            "limits": {window: {limit: int, used: int, remaining: int}},
            "message": str  (only when not allowed),
        }
    """
    user = user or frappe.session.user

    rule = _get_rate_limit_rule(capability)
    if not rule:
        return {"allowed": True, "capability": capability, "limits": {}}

    scope_key = _scope_key(capability, user, rule.get("scope", "Per User"))
    now_ts = time.time()
    limits_info = {}
    blocked_window = None

    for window, duration in _WINDOWS.items():
        max_val = rule.get(_LIMIT_FIELDS[window]) or 0
        if max_val <= 0:
            continue

        key = f"{_RATE_PREFIX}{scope_key}:{window}"
        cutoff = now_ts - duration

        # Count entries within the window
        used = _count_in_window(key, cutoff, now_ts)
        remaining = max(0, max_val - used)

        limits_info[window] = {
            "limit": max_val,
            "used": used,
            "remaining": remaining,
        }

        if remaining <= 0 and not blocked_window:
            blocked_window = window

    if blocked_window:
        info = limits_info[blocked_window]
        return {
            "allowed": False,
            "capability": capability,
            "limits": limits_info,
            "blocked_window": blocked_window,
            "message": (
                f"Rate limit exceeded for '{capability}': "
                f"{info['used']}/{info['limit']} per {blocked_window}."
            ),
        }

    return {"allowed": True, "capability": capability, "limits": limits_info}


def record_usage(capability: str, user: str | None = None):
    """
    Record a capability usage event. Call after successful action.

    Adds a timestamp entry to each active window's sorted set.
    """
    user = user or frappe.session.user

    rule = _get_rate_limit_rule(capability)
    if not rule:
        return

    scope_key = _scope_key(capability, user, rule.get("scope", "Per User"))
    now_ts = time.time()

    for window, duration in _WINDOWS.items():
        max_val = rule.get(_LIMIT_FIELDS[window]) or 0
        if max_val <= 0:
            continue

        key = f"{_RATE_PREFIX}{scope_key}:{window}"
        _add_to_window(key, now_ts, duration)


def get_usage_stats(capability: str, user: str | None = None) -> dict:
    """
    Get current usage statistics for a capability.

    Returns: {window: {limit, used, remaining}} for each active window.
    """
    user = user or frappe.session.user

    rule = _get_rate_limit_rule(capability)
    if not rule:
        return {}

    scope_key = _scope_key(capability, user, rule.get("scope", "Per User"))
    now_ts = time.time()
    stats = {}

    for window, duration in _WINDOWS.items():
        max_val = rule.get(_LIMIT_FIELDS[window]) or 0
        if max_val <= 0:
            continue

        key = f"{_RATE_PREFIX}{scope_key}:{window}"
        cutoff = now_ts - duration
        used = _count_in_window(key, cutoff, now_ts)

        stats[window] = {
            "limit": max_val,
            "used": used,
            "remaining": max(0, max_val - used),
        }

    return stats


def reset_usage(capability: str, user: str | None = None):
    """Reset all rate limit counters for a capability + user."""
    user = user or frappe.session.user

    rule = _get_rate_limit_rule(capability)
    if not rule:
        return

    scope_key = _scope_key(capability, user, rule.get("scope", "Per User"))

    for window in _WINDOWS:
        key = f"{_RATE_PREFIX}{scope_key}:{window}"
        frappe.cache.delete_value(key)


def notify_rate_limit_reached(capability: str, user: str, window: str, limit: int):
    """Create a notification when rate limit is hit."""
    try:
        frappe.get_doc({
            "doctype": "Notification Log",
            "for_user": user,
            "type": "Alert",
            "document_type": "Capability Rate Limit",
            "subject": f"Rate limit reached: {capability}",
            "email_content": (
                f"You have reached the {window} rate limit ({limit}) "
                f"for capability '{capability}'."
            ),
        }).insert(ignore_permissions=True)
    except Exception:
        pass


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  INTERNALS                                                           ║
# ╚═══════════════════════════════════════════════════════════════════════╝


def _get_rate_limit_rule(capability: str) -> dict | None:
    """Get the active rate limit rule for a capability. Cached."""
    cache_key = "caps:rate_rules"
    rules = frappe.cache.get_value(cache_key)

    if rules is None:
        rows = frappe.get_all(
            "Capability Rate Limit",
            filters={"is_active": 1},
            fields=[
                "capability", "max_per_hour", "max_per_day",
                "max_per_week", "max_per_month", "scope", "notify_on_limit",
            ],
        )
        rules = {r["capability"]: r for r in rows}
        frappe.cache.set_value(cache_key, rules, expires_in_sec=300)

    return rules.get(capability)


def _scope_key(capability: str, user: str, scope: str) -> str:
    """Build the Redis key scope portion."""
    if scope == "Global":
        return f"global:{capability}"
    return f"user:{user}:{capability}"


def _count_in_window(key: str, cutoff: float, now_ts: float) -> int:
    """Count sorted set entries between cutoff and now."""
    r = frappe.cache
    # Use raw Redis sorted set operations
    try:
        val = r.get_value(key)
        if not val:
            return 0
        # val is a list of [timestamp, ...] entries
        if isinstance(val, list):
            return sum(1 for ts in val if cutoff <= ts <= now_ts)
        return 0
    except Exception:
        return 0


def _add_to_window(key: str, now_ts: float, ttl: int):
    """Add a timestamp entry to a window's list in Redis."""
    r = frappe.cache
    try:
        val = r.get_value(key) or []
        if not isinstance(val, list):
            val = []
        # Prune old entries outside the window
        cutoff = now_ts - ttl
        val = [ts for ts in val if ts > cutoff]
        val.append(now_ts)
        r.set_value(key, val, expires_in_sec=ttl)
    except Exception:
        pass
