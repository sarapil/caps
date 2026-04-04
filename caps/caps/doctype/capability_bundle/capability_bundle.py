# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

from frappe.model.document import Document


class CapabilityBundle(Document):
    def validate(self):
        self._check_duplicates()

    def _check_duplicates(self):
        seen = set()
        for row in self.capabilities:
            if row.capability in seen:
                from frappe import throw

                throw(f"Duplicate capability: {row.capability}")
            seen.add(row.capability)
