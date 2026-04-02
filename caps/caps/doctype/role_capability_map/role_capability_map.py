# Copyright (c) 2026, Arkan Labs and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class RoleCapabilityMap(Document):
    def autoname(self):
        self.name = self.role
