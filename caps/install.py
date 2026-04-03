"""CAPS — Install / Uninstall hooks."""

import frappe


def after_install():
    """Create default roles and seed initial data."""
    _create_roles()
    # ── Desktop Icon injection (Frappe v16 /desk) ──
    from caps.desktop_utils import inject_app_desktop_icon
    inject_app_desktop_icon(
        app="caps",
        label="CAPS",
        route="/desk/caps-admin",
        logo_url="/assets/caps/images/caps-logo-animated.svg",
        bg_color="#10B981",
    )
    frappe.db.commit()


def before_uninstall():
    """Clean up CAPS data."""
    pass


def _create_roles():
    for role_name in ("CAPS Admin", "CAPS Manager"):
        if not frappe.db.exists("Role", role_name):
            frappe.get_doc({
                "doctype": "Role",
                "role_name": role_name,
                "desk_access": 1,
            }).insert(ignore_permissions=True)
