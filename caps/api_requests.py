"""
CAPS Request Workflow API
==========================

Endpoints for the capability request self-service workflow:
  - Users submit requests for capabilities they need
  - CAPS Managers / Admins review and approve/reject
  - Approved requests auto-grant the capability
"""

import frappe
from frappe.utils import now_datetime


@frappe.whitelist()
def submit_request(
    capability: str,
    reason: str,
    priority: str = "Medium",
    expires_on: str | None = None,
) -> dict:
    """
    Submit a new capability request.

    Any logged-in user can request a capability.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Guest users cannot submit capability requests")

    doc = frappe.get_doc({
        "doctype": "Capability Request",
        "user": user,
        "capability": capability,
        "reason": reason,
        "priority": priority,
        "expires_on": expires_on or None,
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    # Audit
    _audit_request("request_submitted", user, capability, doc.name)

    # Notify approvers
    _notify_approvers(doc)

    return {"status": "submitted", "request": doc.name}


@frappe.whitelist()
def approve_request(
    request_name: str,
    resolution_note: str | None = None,
    expires_on: str | None = None,
) -> dict:
    """
    Approve a pending capability request.

    Requires CAPS Manager, CAPS Admin, or System Manager role.
    """
    frappe.only_for(["System Manager", "CAPS Admin", "CAPS Manager"])

    doc = frappe.get_doc("Capability Request", request_name)
    doc.approve(resolution_note=resolution_note, expires_on=expires_on)
    frappe.db.commit()

    return {"status": "approved", "request": request_name, "user": doc.user, "capability": doc.capability}


@frappe.whitelist()
def reject_request(
    request_name: str,
    resolution_note: str | None = None,
) -> dict:
    """
    Reject a pending capability request.

    Requires CAPS Manager, CAPS Admin, or System Manager role.
    """
    frappe.only_for(["System Manager", "CAPS Admin", "CAPS Manager"])

    doc = frappe.get_doc("Capability Request", request_name)
    doc.reject(resolution_note=resolution_note)
    frappe.db.commit()

    # Audit
    _audit_request("request_rejected", frappe.session.user, doc.capability, request_name)

    return {"status": "rejected", "request": request_name}


@frappe.whitelist()
def cancel_request(request_name: str) -> dict:
    """
    Cancel a pending request. Only the requester can cancel their own request.
    """
    doc = frappe.get_doc("Capability Request", request_name)
    if doc.user != frappe.session.user:
        frappe.only_for(["System Manager", "CAPS Admin"])

    doc.cancel_request()
    frappe.db.commit()

    return {"status": "cancelled", "request": request_name}


@frappe.whitelist()
def get_my_requests(status: str | None = None) -> list[dict]:
    """Return the current user's capability requests."""
    frappe.only_for(["System Manager", "CAPS Admin", "CAPS User"])
    filters = {"user": frappe.session.user}
    if status:
        filters["status"] = status

    return frappe.get_all(
        "Capability Request",
        filters=filters,
        fields=["name", "capability", "status", "priority", "reason", "approver", "resolved_on", "creation"],
        order_by="creation desc",
    )


@frappe.whitelist()
def get_pending_requests() -> list[dict]:
    """Return all pending requests (for approvers)."""
    frappe.only_for(["System Manager", "CAPS Admin", "CAPS Manager"])

    return frappe.get_all(
        "Capability Request",
        filters={"status": "Pending"},
        fields=["name", "user", "capability", "priority", "reason", "creation"],
        order_by="creation desc",
    )


# ─── Helpers ──────────────────────────────────────────────────────────


def _notify_approvers(request_doc):
    """Notify CAPS Managers and Admins about a new request."""
    try:
        from caps.notifications import notify_request_submitted
        notify_request_submitted(request_doc.name, request_doc.user, request_doc.capability)
    except Exception:
        pass


def _audit_request(action: str, user: str, capability: str, request_name: str):
    """Log request action to audit trail."""
    try:
        frappe.get_doc({
            "doctype": "CAPS Audit Log",
            "user": user,
            "action": action,
            "capability": capability,
            "target_user": user,
            "result": "allowed",
            "context": frappe.as_json({"request": request_name}),
            "timestamp": now_datetime(),
            "ip_address": getattr(frappe.local, "request_ip", ""),
        }).insert(ignore_permissions=True)
    except Exception:
        pass
