# Copyright (c) 2026, Arkan Labs and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CapabilityRateLimit(Document):
    def validate(self):
        for field in ("max_per_hour", "max_per_day", "max_per_week", "max_per_month"):
            val = getattr(self, field, 0) or 0
            if val < 0:
                frappe.throw(f"{field} cannot be negative")

        # At least one limit must be set
        limits = [
            self.max_per_hour or 0,
            self.max_per_day or 0,
            self.max_per_week or 0,
            self.max_per_month or 0,
        ]
        if all(l == 0 for l in limits):
            frappe.throw("At least one usage limit must be set (non-zero).")
