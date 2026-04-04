# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class CapabilityRequest(Document):
    def validate(self):
        self._validate_capability()
        self._validate_not_duplicate()

    def _validate_capability(self):
        """Ensure the requested capability exists and is active."""
        if not frappe.db.exists("Capability", self.capability):
            frappe.throw(f"Capability '{self.capability}' does not exist")

        cap = frappe.get_doc("Capability", self.capability)
        if not cap.is_active:
            frappe.throw(f"Capability '{self.capability}' is inactive")

    def _validate_not_duplicate(self):
        """Prevent duplicate pending requests for the same user + capability."""
        if self.is_new():
            existing = frappe.db.exists(
                "Capability Request",
                {
                    "user": self.user,
                    "capability": self.capability,
                    "status": "Pending",
                    "name": ("!=", self.name),
                },
            )
            if existing:
                frappe.throw(
                    f"A pending request already exists for {self.user} → {self.capability}"
                )

    def approve(self, resolution_note: str | None = None, expires_on: str | None = None):
        """Approve the request and auto-grant the capability."""
        if self.status != "Pending":
            frappe.throw(f"Cannot approve a request with status: {self.status}")

        self.status = "Approved"
        self.approver = frappe.session.user
        self.resolved_on = now_datetime()
        if resolution_note:
            self.resolution_note = resolution_note
        if expires_on:
            self.expires_on = expires_on
        self.save(ignore_permissions=True)

        # Auto-grant the capability
        self._grant_capability()

        # Notify the requester
        from caps.notifications import notify_request_approved
        notify_request_approved(self.name, self.user, self.capability,
                                approver=frappe.session.user, note=resolution_note)

    def reject(self, resolution_note: str | None = None):
        """Reject the request."""
        if self.status != "Pending":
            frappe.throw(f"Cannot reject a request with status: {self.status}")

        self.status = "Rejected"
        self.approver = frappe.session.user
        self.resolved_on = now_datetime()
        if resolution_note:
            self.resolution_note = resolution_note
        self.save(ignore_permissions=True)

        from caps.notifications import notify_request_rejected
        notify_request_rejected(self.name, self.user, self.capability,
                                approver=frappe.session.user, note=resolution_note)

    def cancel_request(self):
        """Cancel a pending request (by the requester)."""
        if self.status != "Pending":
            frappe.throw(f"Cannot cancel a request with status: {self.status}")

        self.status = "Cancelled"
        self.resolved_on = now_datetime()
        self.save(ignore_permissions=True)

    def _grant_capability(self):
        """Grant the requested capability to the user."""
        from caps.utils.resolver import invalidate_user_cache

        user = self.user
        if not frappe.db.exists("User Capability", user):
            frappe.get_doc({
                "doctype": "User Capability",
                "user": user,
            }).insert(ignore_permissions=True)

        doc = frappe.get_doc("User Capability", user)

        # Skip if already has it
        for row in doc.direct_capabilities:
            if row.capability == self.capability:
                return

        doc.append("direct_capabilities", {
            "capability": self.capability,
            "granted_by": self.approver,
            "granted_on": now_datetime(),
            "expires_on": self.expires_on or None,
        })
        doc.save(ignore_permissions=True)
        invalidate_user_cache(user)

        # Audit
        try:
            frappe.get_doc({
                "doctype": "CAPS Audit Log",
                "user": self.approver,
                "action": "request_approved",
                "capability": self.capability,
                "target_user": user,
                "result": "allowed",
                "context": frappe.as_json({"request": self.name}),
                "timestamp": now_datetime(),
                "ip_address": getattr(frappe.local, "request_ip", ""),
            }).insert(ignore_permissions=True)
        except Exception:
            pass

    def _notify_user(self, message: str):
        """Send notification to the requesting user."""
        try:
            frappe.get_doc({
                "doctype": "Notification Log",
                "for_user": self.user,
                "from_user": frappe.session.user,
                "type": "Alert",
                "subject": f"CAPS Request: {self.capability}",
                "email_content": message,
            }).insert(ignore_permissions=True)
        except Exception:
            pass
