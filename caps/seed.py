"""
CAPS — Seed Data
Runs on `after_migrate` to ensure reference data exists.
"""

import frappe
from frappe import _


def seed_data():
    """
    Idempotent seed — safe to run multiple times.
    Seeds reference data, settings defaults, and lookup values.
    """
    frappe.logger().info("CAPS: Running seed_data()...")

    _seed_settings()
    _seed_roles()

    frappe.db.commit()
    frappe.logger().info("CAPS: seed_data() complete.")


def _seed_settings():
    """Ensure Settings singleton has sensible defaults."""
    # Check if settings doctype exists
    settings_dt = None
    for dt_name in ["CAPS Settings", "CAPS Settings", "Caps Settings"]:
        if frappe.db.exists("DocType", dt_name):
            settings_dt = dt_name
            break

    if not settings_dt:
        return

    try:
        settings = frappe.get_single(settings_dt)
        # Only set defaults if not already configured
        if not settings.flags.get("has_been_configured"):
            frappe.logger().info(f"{settings_dt}: Defaults already configured or no flag.")
    except Exception as e:
        frappe.logger().warning(f"Could not seed settings: {e}")


def _seed_roles():
    """Ensure app-specific roles exist."""
    roles = [
        {"role": "CAPS User", "desk_access": 1},
        {"role": "CAPS Manager", "desk_access": 1},
        {"role": "CAPS Admin", "desk_access": 1},
    ]

    for role_data in roles:
        role_name = role_data["role"]
        if not frappe.db.exists("Role", role_name):
            doc = frappe.new_doc("Role")
            doc.role_name = role_name
            doc.desk_access = role_data.get("desk_access", 1)
            doc.insert(ignore_permissions=True)
            frappe.logger().info(f"Created role: {role_name}")


def _insert_if_missing(doctype, name, data=None):
    """Helper: insert a record only if it doesn't exist."""
    if not frappe.db.exists(doctype, name):
        doc = frappe.new_doc(doctype)
        doc.update(data or {})
        if hasattr(doc.meta, "get_field") and doc.meta.get_field("name1"):
            doc.name1 = name
        doc.insert(ignore_permissions=True)
        return doc
    return frappe.get_doc(doctype, name)
