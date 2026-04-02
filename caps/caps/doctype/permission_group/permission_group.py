# Copyright (c) 2026, Arkan Labs and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class PermissionGroup(Document):
    def validate(self):
        self._stamp_new_members()
        self._prevent_circular_parent()

    def _stamp_new_members(self):
        for row in self.members:
            if not row.added_on:
                row.added_on = now_datetime()
            if not row.added_by:
                row.added_by = frappe.session.user

    def _prevent_circular_parent(self):
        if not self.parent_group:
            return
        visited = {self.name}
        current = self.parent_group
        while current:
            if current in visited:
                frappe.throw(_("Circular parent group reference detected."))
            visited.add(current)
            current = frappe.db.get_value("Permission Group", current, "parent_group")
