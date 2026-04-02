# Copyright (c) 2026, Arkan Labs and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CAPSSettings(Document):
    def validate(self):
        self._validate_ttl_ranges()
        self._validate_retention_days()

    def _validate_ttl_ranges(self):
        if self.cache_ttl is not None and self.cache_ttl < 10:
            frappe.throw("User Cache TTL must be at least 10 seconds.")
        if self.cache_ttl and self.cache_ttl > 86400:
            frappe.throw("User Cache TTL cannot exceed 86400 seconds (24 hours).")

        if self.field_map_cache_ttl is not None and self.field_map_cache_ttl < 10:
            frappe.throw("Field/Action Map Cache TTL must be at least 10 seconds.")
        if self.field_map_cache_ttl and self.field_map_cache_ttl > 86400:
            frappe.throw("Field/Action Map Cache TTL cannot exceed 86400 seconds (24 hours).")

    def _validate_retention_days(self):
        if self.audit_retention_days is not None and self.audit_retention_days < 1:
            frappe.throw("Audit Log Retention must be at least 1 day.")
        if self.audit_retention_days and self.audit_retention_days > 3650:
            frappe.throw("Audit Log Retention cannot exceed 3650 days (10 years).")

    def on_update(self):
        """Apply settings changes immediately."""
        from caps.utils.resolver import invalidate_all_caches, invalidate_field_action_caches
        # Invalidate caches so new TTL values take effect
        invalidate_all_caches()
        invalidate_field_action_caches()
