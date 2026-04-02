"""
CAPS — Notification Engine
============================

Central notification module for all CAPS events.

Notification channels:
1. Notification Log (bell icon)
2. frappe.publish_realtime (push to open tabs)
3. Email (for critical events when configured)

All notification creation is best-effort — failures are logged but
never break the calling operation.
"""

import frappe
from frappe.utils import now_datetime


# ─── Public API ───────────────────────────────────────────────────────


def notify_capability_change(user: str, granted: list[str] | None = None,
                             revoked: list[str] | None = None,
                             changed_by: str | None = None):
    """Notify a user that their capabilities have changed."""
    if not _is_notify_on_change_enabled():
        return

    granted = granted or []
    revoked = revoked or []

    if not granted and not revoked:
        return

    parts = []
    if granted:
        parts.append(f"Granted: {', '.join(granted)}")
    if revoked:
        parts.append(f"Revoked: {', '.join(revoked)}")

    subject = f"CAPS: Your capabilities have been updated"
    message = "\n".join(parts)

    _create_notification(
        for_user=user,
        from_user=changed_by or "Administrator",
        subject=subject,
        message=message,
    )

    _publish_realtime(
        event="caps_capability_change",
        user=user,
        data={
            "granted": granted,
            "revoked": revoked,
            "changed_by": changed_by or "Administrator",
        },
    )


def notify_request_submitted(request_name: str, user: str, capability: str):
    """Notify CAPS admins/managers about a new capability request."""
    approvers = _get_approvers(exclude=user)
    subject = f"CAPS: New request from {user} for '{capability}'"
    message = (
        f"User {user} has submitted a capability request for '{capability}'.\n"
        f"Request: {request_name}"
    )

    for approver in approvers:
        _create_notification(
            for_user=approver,
            from_user=user,
            subject=subject,
            message=message,
            doc_type="Capability Request",
            doc_name=request_name,
        )

    if _is_email_on_request_enabled() and approvers:
        _send_email(
            recipients=approvers,
            subject=subject,
            message=message,
            reference_doctype="Capability Request",
            reference_name=request_name,
        )


def notify_request_approved(request_name: str, user: str, capability: str,
                            approver: str, note: str | None = None):
    """Notify the requester that their request was approved."""
    subject = f"CAPS: Request approved — '{capability}'"
    message = f"Your request for capability '{capability}' has been approved by {approver}."
    if note:
        message += f"\nNote: {note}"

    _create_notification(
        for_user=user,
        from_user=approver,
        subject=subject,
        message=message,
        doc_type="Capability Request",
        doc_name=request_name,
    )

    _publish_realtime(
        event="caps_request_approved",
        user=user,
        data={"request": request_name, "capability": capability},
    )


def notify_request_rejected(request_name: str, user: str, capability: str,
                            approver: str, note: str | None = None):
    """Notify the requester that their request was rejected."""
    subject = f"CAPS: Request rejected — '{capability}'"
    message = f"Your request for capability '{capability}' has been rejected by {approver}."
    if note:
        message += f"\nReason: {note}"

    _create_notification(
        for_user=user,
        from_user=approver,
        subject=subject,
        message=message,
        doc_type="Capability Request",
        doc_name=request_name,
    )

    _publish_realtime(
        event="caps_request_rejected",
        user=user,
        data={"request": request_name, "capability": capability},
    )


def notify_delegation(delegator: str, delegatee: str, capability: str,
                      action: str = "granted"):
    """Notify a user about a delegation event."""
    if not _is_notify_on_change_enabled():
        return

    if action == "granted":
        subject = f"CAPS: '{capability}' delegated to you"
        message = f"{delegator} has delegated capability '{capability}' to you."
    else:
        subject = f"CAPS: '{capability}' delegation revoked"
        message = f"{delegator} has revoked the delegated capability '{capability}'."

    _create_notification(
        for_user=delegatee,
        from_user=delegator,
        subject=subject,
        message=message,
    )

    _publish_realtime(
        event="caps_delegation_change",
        user=delegatee,
        data={"capability": capability, "delegator": delegator, "action": action},
    )


def notify_expiry_warning(user: str, expiries: list[dict], warning_days: int):
    """Notify a user about expiring capabilities/bundles."""
    items = []
    for e in expiries:
        items.append(f"• {e['type'].title()}: {e['name']} (expires {e['expires_on'][:10]})")

    subject = f"CAPS: {len(expiries)} grant(s) expiring within {warning_days} days"
    message = "The following CAPS grants are expiring soon:\n\n" + "\n".join(items)

    _create_notification(
        for_user=user,
        from_user="Administrator",
        subject=subject,
        message=message,
    )

    _publish_realtime(
        event="caps_expiry_warning",
        user=user,
        data={"expiries": expiries, "warning_days": warning_days},
    )


def notify_policy_applied(user: str, policy_name: str, capabilities: list[str]):
    """Notify a user when a policy auto-grants capabilities."""
    if not _is_notify_on_change_enabled():
        return

    subject = f"CAPS: Policy '{policy_name}' applied"
    message = (
        f"Policy '{policy_name}' has granted you the following capabilities:\n"
        + "\n".join(f"• {c}" for c in capabilities)
    )

    _create_notification(
        for_user=user,
        from_user="Administrator",
        subject=subject,
        message=message,
    )


def send_admin_digest():
    """
    Weekly admin digest: send summary email to all CAPS Admins.
    Includes: new requests, grants/revokes, policy activity, expiring soon.
    """
    if not _is_admin_digest_enabled():
        return

    from frappe.utils import add_days
    week_ago = add_days(now_datetime(), -7)
    admins = _get_approvers()

    if not admins:
        return

    # Gather stats
    new_requests = frappe.db.count("Capability Request", {"creation": (">=", week_ago)})
    approved = frappe.db.count("Capability Request", {
        "status": "Approved", "resolved_on": (">=", week_ago)
    })
    rejected = frappe.db.count("Capability Request", {
        "status": "Rejected", "resolved_on": (">=", week_ago)
    })
    audit_count = frappe.db.count("CAPS Audit Log", {"timestamp": (">=", week_ago)})
    expiring_soon = frappe.db.count("User Capability Item", {
        "expires_on": ("is", "set"),
        "expires_on": ("<=", add_days(now_datetime(), 7)),
        "expires_on": (">", now_datetime()),
    })

    subject = f"CAPS Weekly Digest — {now_datetime().strftime('%Y-%m-%d')}"
    message = (
        f"<h3>CAPS Weekly Summary</h3>"
        f"<table border='1' cellpadding='5' cellspacing='0'>"
        f"<tr><td><b>New Requests</b></td><td>{new_requests}</td></tr>"
        f"<tr><td><b>Approved</b></td><td>{approved}</td></tr>"
        f"<tr><td><b>Rejected</b></td><td>{rejected}</td></tr>"
        f"<tr><td><b>Audit Log Entries</b></td><td>{audit_count}</td></tr>"
        f"<tr><td><b>Grants Expiring Soon</b></td><td>{expiring_soon}</td></tr>"
        f"</table>"
    )

    _send_email(
        recipients=admins,
        subject=subject,
        message=message,
        now=True,
    )


# ─── Settings Helpers ─────────────────────────────────────────────────


def _is_notify_on_change_enabled() -> bool:
    try:
        from caps.settings_helper import get_caps_settings
        return get_caps_settings().notify_on_capability_change
    except Exception:
        return True


def _is_email_on_request_enabled() -> bool:
    try:
        from caps.settings_helper import get_caps_settings
        return get_caps_settings().email_on_request
    except Exception:
        return False


def _is_admin_digest_enabled() -> bool:
    try:
        from caps.settings_helper import get_caps_settings
        return get_caps_settings().enable_admin_digest
    except Exception:
        return False


# ─── Internal Helpers ─────────────────────────────────────────────────


def _get_approvers(exclude: str | None = None) -> list[str]:
    """Get all users with CAPS Admin or CAPS Manager role."""
    users = set()
    for role in ("CAPS Admin", "CAPS Manager"):
        members = frappe.get_all(
            "Has Role",
            filters={"role": role, "parenttype": "User"},
            pluck="parent",
        )
        users.update(members)

    # Also add System Manager users
    sm_users = frappe.get_all(
        "Has Role",
        filters={"role": "System Manager", "parenttype": "User"},
        pluck="parent",
    )
    users.update(sm_users)

    # Filter out disabled users and the excluded user
    active_users = frappe.get_all(
        "User",
        filters={"name": ("in", list(users)), "enabled": 1},
        pluck="name",
    )

    if exclude:
        active_users = [u for u in active_users if u != exclude]

    return active_users


def _create_notification(for_user: str, from_user: str, subject: str,
                         message: str, doc_type: str | None = None,
                         doc_name: str | None = None):
    """Create a Notification Log entry (bell icon notification)."""
    try:
        doc = frappe.get_doc({
            "doctype": "Notification Log",
            "for_user": for_user,
            "from_user": from_user,
            "type": "Alert",
            "subject": subject,
            "email_content": message,
        })
        if doc_type:
            doc.document_type = doc_type
        if doc_name:
            doc.document_name = doc_name
        doc.insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(
            title="CAPS Notification Error",
            message=frappe.get_traceback(),
        )


def _publish_realtime(event: str, user: str, data: dict):
    """Push real-time event to the user's browser session."""
    try:
        frappe.publish_realtime(
            event=event,
            message=data,
            user=user,
        )
    except Exception:
        pass


def _send_email(recipients: list[str], subject: str, message: str,
                reference_doctype: str | None = None,
                reference_name: str | None = None,
                now: bool = False):
    """Send email notification."""
    try:
        frappe.sendmail(
            recipients=recipients,
            subject=subject,
            message=message,
            reference_doctype=reference_doctype,
            reference_name=reference_name,
            now=now,
        )
    except Exception:
        frappe.log_error(
            title="CAPS Email Error",
            message=frappe.get_traceback(),
        )


# ─── Frappe Notification Config Hook ────────────────────────────────


def get_notification_config():
    """
    Hook for Frappe's get_notification_config.

    Returns counts for the navbar bell icon badge:
    - Pending Capability Requests (for approvers)
    - Pending Delegation Requests (for delegates)

    Configured via `get_notification_config` in hooks.py.
    """
    return {
        "for_doctype": {
            "Capability Request": {"status": "Pending"},
        },
        "for_module_doctypes": {
            "CAPS": ["Capability Request"],
        },
    }
