# Copyright (c) 2026, Arkan Labs and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class UserCapability(Document):
    def autoname(self):
        self.name = self.user

    def validate(self):
        self._stamp_grants()

    def _stamp_grants(self):
        now = now_datetime()
        user = frappe.session.user
        for row in self.direct_capabilities:
            if not row.granted_on:
                row.granted_on = now
            if not row.granted_by:
                row.granted_by = user
        for row in self.direct_bundles:
            if not row.granted_on:
                row.granted_on = now
            if not row.granted_by:
                row.granted_by = user
