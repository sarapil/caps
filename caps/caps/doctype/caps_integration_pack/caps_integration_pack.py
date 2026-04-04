# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

import json
import frappe
from frappe.model.document import Document


class CAPSIntegrationPack(Document):
    def validate(self):
        if self.config_json:
            try:
                json.loads(self.config_json)
            except (json.JSONDecodeError, TypeError):
                frappe.throw("Pack Configuration JSON is not valid JSON.")
