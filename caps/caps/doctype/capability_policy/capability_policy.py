# Copyright (c) 2026, CAPS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, getdate


class CapabilityPolicy(Document):
    """Temporal policy that auto-grants capabilities to groups of users."""

    def validate(self):
        self._validate_grant()
        self._validate_schedule()
        self._validate_target()

    def _validate_grant(self):
        """Ensure exactly one of capability or bundle is set, matching grant_type."""
        if self.grant_type == "Capability":
            if not self.capability:
                frappe.throw("Capability is required when Grant Type is 'Capability'")
            if self.bundle:
                frappe.throw("Bundle must be empty when Grant Type is 'Capability'")
            # Validate capability exists and is active
            cap = frappe.db.get_value("Capability", self.capability, ["is_active"], as_dict=True)
            if not cap:
                frappe.throw(f"Capability '{self.capability}' does not exist")
            if not cap.is_active:
                frappe.throw(f"Capability '{self.capability}' is not active")
        else:
            if not self.bundle:
                frappe.throw("Bundle is required when Grant Type is 'Bundle'")
            if self.capability:
                frappe.throw("Capability must be empty when Grant Type is 'Bundle'")

    def _validate_schedule(self):
        """Ensure ends_on > starts_on if both are set."""
        if self.starts_on and self.ends_on:
            if self.ends_on <= self.starts_on:
                frappe.throw("Ends On must be after Starts On")

    def _validate_target(self):
        """Validate target-type-specific fields."""
        if self.target_type == "Role" and not self.target_role:
            frappe.throw("Target Role is required when Target Type is 'Role'")
        elif self.target_type == "Department" and not self.target_department:
            frappe.throw("Target Department is required when Target Type is 'Department'")
        elif self.target_type == "User List":
            if not self.target_users:
                frappe.throw("Target Users is required when Target Type is 'User List'")
            # Validate emails
            emails = [e.strip() for e in self.target_users.split(",") if e.strip()]
            if not emails:
                frappe.throw("At least one user email is required in Target Users")

    def is_currently_active(self):
        """Check if this policy is active and within its schedule window."""
        if not self.is_active:
            return False
        current = now_datetime()
        if self.starts_on and current < self.starts_on:
            return False
        if self.ends_on and current > self.ends_on:
            return False
        return True

    def get_target_users(self):
        """Resolve the list of user emails this policy targets."""
        if self.target_type == "Role":
            return _get_users_with_role(self.target_role)
        elif self.target_type == "Department":
            return _get_users_in_department(self.target_department)
        elif self.target_type == "User List":
            return [e.strip() for e in self.target_users.split(",") if e.strip()]
        return []

    def get_grant_items(self):
        """Return list of capability names this policy grants."""
        if self.grant_type == "Capability":
            return [self.capability]
        else:
            # Expand bundle into individual capabilities
            items = frappe.get_all(
                "Capability Bundle Item",
                filters={"parent": self.bundle},
                fields=["capability"],
            )
            return [i.capability for i in items]


def _get_users_with_role(role):
    """Get all enabled users that have a specific role."""
    return frappe.get_all(
        "Has Role",
        filters={"role": role, "parenttype": "User"},
        fields=["parent"],
        pluck="parent",
    )


def _get_users_in_department(department):
    """Get all enabled users in a department via Employee."""
    employees = frappe.get_all(
        "Employee",
        filters={"department": department, "status": "Active"},
        fields=["user_id"],
        pluck="user_id",
    )
    return [e for e in employees if e]
