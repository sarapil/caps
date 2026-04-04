# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS — Demo Data
Load/clear demo data for CAPS showcases.
All demo records are tagged with `_is_demo = 1` for safe removal.
"""

import frappe
from frappe import _


def load_demo_data():
    """Load demonstration data for CAPS.

    All records created here must include `_is_demo: 1` custom field
    so they can be safely removed by `clear_demo_data()`.
    """
    frappe.flags.in_demo = True
    try:
        _create_demo_records()
        frappe.db.commit()
        frappe.msgprint(_("Demo data loaded for CAPS"))
    finally:
        frappe.flags.in_demo = False


def clear_demo_data():
    """Remove all demo data created by `load_demo_data()`.

    Finds and deletes all records with `_is_demo = 1`.
    """
    demo_doctypes = _get_demo_doctypes()
    for dt in reversed(demo_doctypes):
        names = frappe.get_all(dt, filters={"_is_demo": 1}, pluck="name")
        for name in names:
            frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
    frappe.db.commit()
    frappe.msgprint(_("Demo data cleared for CAPS"))


def _create_demo_records():
    """Create demo records. Override per app."""
    pass  # TODO: Implement app-specific demo data


def _get_demo_doctypes() -> list[str]:
    """Return list of DocTypes that may contain demo data, in dependency order."""
    return []  # TODO: Populate with app-specific DocTypes
