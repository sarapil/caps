# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS – Rate Limit API
======================

Whitelisted endpoints for checking and managing capability rate limits.
"""

import frappe


@frappe.whitelist()
def check_rate_limit(capability: str) -> dict:
    """Check if the current user is within rate limits for a capability."""
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])

    from caps.rate_limiter import check_rate_limit as _check
    return _check(capability, frappe.session.user)


@frappe.whitelist()
def record_usage(capability: str):
    """Record a usage event for a capability."""
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])

    from caps.rate_limiter import record_usage as _record
    _record(capability, frappe.session.user)


@frappe.whitelist()
def get_usage_stats(capability: str) -> dict:
    """Get usage statistics for the current user and a capability."""
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])

    from caps.rate_limiter import get_usage_stats as _stats
    return _stats(capability, frappe.session.user)


@frappe.whitelist()
def reset_user_usage(capability: str, user: str | None = None):
    """Reset rate limit counters for a user (admin only)."""
    frappe.only_for(["System Manager"])

    from caps.rate_limiter import reset_usage
    reset_usage(capability, user or frappe.session.user)
    return {"status": "ok"}


@frappe.whitelist()
def get_all_rate_limits() -> list[dict]:
    """List all active rate limit rules (admin only)."""
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    return frappe.get_all(
        "Capability Rate Limit",
        filters={"is_active": 1},
        fields=[
            "name", "capability", "max_per_hour", "max_per_day",
            "max_per_week", "max_per_month", "scope", "notify_on_limit",
        ],
        order_by="capability",
    )
