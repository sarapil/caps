# Copyright (c) 2026, Arkan Labs and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class FieldCapabilityMap(Document):
    def validate(self):
        self._fetch_field_label()
        self._validate_fieldname()

    def _fetch_field_label(self):
        if self.doctype_name and self.fieldname:
            meta = frappe.get_meta(self.doctype_name)
            field = meta.get_field(self.fieldname)
            if field:
                self.field_label = field.label

    def _validate_fieldname(self):
        if self.doctype_name and self.fieldname:
            meta = frappe.get_meta(self.doctype_name)
            if not meta.get_field(self.fieldname):
                frappe.throw(
                    f"Field '{self.fieldname}' does not exist on {self.doctype_name}"
                )
