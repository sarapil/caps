# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CAPSSiteProfile(Document):
    def validate(self):
        if self.site_url:
            url = self.site_url.rstrip("/")
            if not url.startswith(("http://", "https://")):
                frappe.throw("Site URL must start with http:// or https://")
            self.site_url = url
