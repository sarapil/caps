"""
CAPS Scheduled Tasks
====================

Hourly:  Expire time-boxed capabilities
Daily:   Sync auto-sync permission groups, cleanup old audit logs
"""

import frappe
from frappe.utils import add_days, now_datetime


def expire_timeboxed_capabilities():
    """Remove expired time-boxed capability and bundle grants."""
    now = now_datetime()

    # Expire direct user capabilities
    expired_caps = frappe.get_all(
        "User Capability Item",
        filters=[
            ["expires_on", "is", "set"],
            ["expires_on", "<", now],
        ],
        fields=["name", "parent", "capability"],
    )

    affected_users = set()
    for row in expired_caps:
        frappe.db.delete("User Capability Item", row["name"])
        affected_users.add(row["parent"])
        # Audit
        _log_expiry(row["parent"], row["capability"])

    # Expire direct user bundles
    expired_bundles = frappe.get_all(
        "User Capability Bundle",
        filters=[
            ["expires_on", "is", "set"],
            ["expires_on", "<", now],
        ],
        fields=["name", "parent", "bundle"],
    )

    for row in expired_bundles:
        frappe.db.delete("User Capability Bundle", row["name"])
        affected_users.add(row["parent"])
        _log_expiry(row["parent"], f"bundle:{row['bundle']}")

    # Invalidate caches
    from caps.utils.resolver import invalidate_user_cache
    for user in affected_users:
        invalidate_user_cache(user)

    if affected_users:
        frappe.db.commit()


def sync_permission_groups():
    """Sync auto-sync permission groups (Department, Branch, Custom Query)."""
    groups = frappe.get_all(
        "Permission Group",
        filters={"auto_sync": 1, "group_type": ("!=", "Manual")},
        fields=["name", "group_type", "sync_source", "sync_query"],
    )

    from caps.utils.resolver import invalidate_user_cache

    for g in groups:
        try:
            users = _resolve_group_members(g)
            if users is None:
                continue

            doc = frappe.get_doc("Permission Group", g["name"])
            existing = {r.user for r in doc.members}
            target = set(users)

            # Add new members
            for user in target - existing:
                doc.append("members", {"user": user})

            # Remove old members
            for row in list(doc.members):
                if row.user not in target:
                    doc.remove(row)

            if existing != target:
                doc.save(ignore_permissions=True)
                for user in existing | target:
                    invalidate_user_cache(user)

        except Exception:
            frappe.log_error(
                title=f"CAPS Group Sync Error: {g['name']}",
                message=frappe.get_traceback(),
            )

    frappe.db.commit()


def cleanup_audit_logs():
    """Delete audit logs older than retention period (from CAPS Settings, default 90 days)."""
    try:
        from caps.settings_helper import get_caps_settings
        retention_days = get_caps_settings().audit_retention_days
    except Exception:
        retention_days = 90

    cutoff = add_days(now_datetime(), -retention_days)
    frappe.db.delete("CAPS Audit Log", {"timestamp": ("<", cutoff)})
    frappe.db.commit()


def warn_expiring_capabilities():
    """
    Daily task: notify users whose time-boxed capabilities expire within
    the warning window (default: 7 days).

    Creates a Frappe system notification for each affected user.
    """
    try:
        from caps.settings_helper import get_caps_settings
        settings = get_caps_settings()
        if not settings.enable_expiry_notifications:
            return
        warning_days = settings.expiry_warning_days
    except Exception:
        warning_days = 7

    if not warning_days or warning_days <= 0:
        return

    now = now_datetime()
    cutoff = add_days(now, warning_days)

    # Find capabilities expiring within the warning window
    expiring_caps = frappe.get_all(
        "User Capability Item",
        filters=[
            ["expires_on", "is", "set"],
            ["expires_on", ">", now],
            ["expires_on", "<=", cutoff],
        ],
        fields=["name", "parent", "capability", "expires_on"],
    )

    # Find bundles expiring within the warning window
    expiring_bundles = frappe.get_all(
        "User Capability Bundle",
        filters=[
            ["expires_on", "is", "set"],
            ["expires_on", ">", now],
            ["expires_on", "<=", cutoff],
        ],
        fields=["name", "parent", "bundle", "expires_on"],
    )

    # Group by user
    user_expiries: dict[str, list[dict]] = {}
    for row in expiring_caps:
        user_expiries.setdefault(row["parent"], []).append({
            "type": "capability",
            "name": row["capability"],
            "expires_on": str(row["expires_on"]),
        })
    for row in expiring_bundles:
        user_expiries.setdefault(row["parent"], []).append({
            "type": "bundle",
            "name": row["bundle"],
            "expires_on": str(row["expires_on"]),
        })

    # Send notification per user
    for user, expiries in user_expiries.items():
        from caps.notifications import notify_expiry_warning
        notify_expiry_warning(user, expiries, warning_days)

    if user_expiries:
        frappe.db.commit()


def _send_expiry_notification(user: str, expiries: list[dict], warning_days: int):
    """Legacy: Create a system notification for a user about expiring capabilities.
    Now delegated to caps.notifications.notify_expiry_warning.
    Kept for backward compatibility."""
    from caps.notifications import notify_expiry_warning
    notify_expiry_warning(user, expiries, warning_days)


# ─── Helpers ──────────────────────────────────────────────────────────


def _resolve_group_members(group: dict) -> list[str] | None:
    """Resolve the member list for an auto-sync group."""
    group_type = group["group_type"]
    source = group.get("sync_source") or ""

    if group_type == "Department Sync" and source:
        return frappe.get_all(
            "Employee",
            filters={"department": source, "status": "Active"},
            pluck="user_id",
        )

    if group_type == "Branch Sync" and source:
        return frappe.get_all(
            "Employee",
            filters={"branch": source, "status": "Active"},
            pluck="user_id",
        )

    if group_type == "Custom Query":
        query = group.get("sync_query") or ""
        if query:
            # Sandboxed eval — only allow frappe.get_all style queries
            try:
                result = frappe.safe_eval(query)
                if isinstance(result, list):
                    return [str(r) for r in result]
            except Exception:
                frappe.log_error(
                    title=f"CAPS Custom Query Error: {group['name']}",
                    message=frappe.get_traceback(),
                )

    return None


def _log_expiry(user: str, capability: str):
    """Log capability expiry in audit trail."""
    try:
        frappe.get_doc({
            "doctype": "CAPS Audit Log",
            "user": "Administrator",
            "action": "capability_revoked",
            "capability": capability,
            "target_user": user,
            "result": "allowed",
            "context": '{"reason": "time_boxed_expiry"}',
            "timestamp": now_datetime(),
        }).insert(ignore_permissions=True)
    except Exception:
        pass


def expire_temp_group_memberships():
    """Remove expired temporary group memberships (valid_till < now)."""
    now = now_datetime()

    expired = frappe.get_all(
        "Permission Group Member",
        filters=[
            ["valid_till", "is", "set"],
            ["valid_till", "<", now],
        ],
        fields=["name", "parent", "user"],
    )

    if not expired:
        return

    affected_users = set()
    affected_groups = set()

    for row in expired:
        frappe.db.delete("Permission Group Member", row["name"])
        affected_users.add(row["user"])
        affected_groups.add(row["parent"])

    from caps.utils.resolver import invalidate_user_cache
    for user in affected_users:
        invalidate_user_cache(user)

    frappe.db.commit()


def weekly_admin_digest():
    """Send weekly summary email to CAPS Admins."""
    from caps.notifications import send_admin_digest
    send_admin_digest()


def warm_caches():
    """Daily task: pre-populate capability caches for active users."""
    from caps.performance import warm_caches as _warm, warm_map_caches
    _warm(max_users=100)
    warm_map_caches()
