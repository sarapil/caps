# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

from frappe.model.document import Document


class RoleCapabilityMap(Document):
    def autoname(self):
        self.name = self.role
