"""
Utility helpers for injecting Desktop Icon and updating Desktop Layouts.

Usage (run inside bench site context):

from candela.desktop_utils import inject_app_desktop_icon
inject_app_desktop_icon(
    app="candela",
    label="Candela",
    route="/desk/candela",
    logo_url="/assets/candela/images/candela-logo.svg",
    bg_color="blue",
)

This will:
- create a `Desktop Icon` doc of type `App` if not exists
- ensure every `Desktop Layout` record has an entry for the app (avoid duplicates)
- clear relevant caches

Designed to be reusable by other apps.
"""

import json
import frappe


def inject_app_desktop_icon(app: str, label: str, route: str, logo_url: str, bg_color: str = "blue"):
    """Create Desktop Icon and add it to all Desktop Layout records.

    Safe to call multiple times (idempotent).
    """
    # Create Desktop Icon if needed
    try:
        existing = frappe.db.get_value(
            "Desktop Icon", {"app": app, "icon_type": "App"}, "name"
        )
        if not existing:
            # If a Desktop Icon with same label exists, skip creating duplicate
            if frappe.db.exists("Desktop Icon", {"label": label, "icon_type": "App"}):
                existing = frappe.db.get_value("Desktop Icon", {"label": label, "icon_type": "App"}, "name")

        if not existing:
            icon = frappe.get_doc(
                {
                    "doctype": "Desktop Icon",
                    "label": label,
                    "icon_type": "App",
                    "app": app,
                    "link": route,
                    "link_type": "External",
                    "logo_url": logo_url,
                    "bg_color": bg_color,
                    "standard": 1,
                    "hidden": 0,
                }
            )
            icon.insert(ignore_permissions=True)
            frappe.db.commit()
    except Exception:
        # best-effort; log and continue
        frappe.log_error(title="inject_app_desktop_icon: create icon failed")

    # Ensure Desktop Layouts include the entry
    try:
        if not frappe.db.exists("DocType", "Desktop Layout"):
            return

        candela_entry = {
            "label": label,
            "bg_color": bg_color,
            "link": route,
            "link_type": "External",
            "app": app,
            "icon_type": "App",
            "parent_icon": None,
            "icon": None,
            "link_to": None,
            "idx": 0,
            "standard": 1,
            "logo_url": logo_url,
            "hidden": 0,
            "name": label,
            "restrict_removal": 0,
            "icon_image": None,
        }

        for layout in frappe.get_all("Desktop Layout", fields=["name", "layout"]):
            try:
                data = json.loads(layout.layout or "[]")
            except Exception:
                data = []

            if any((isinstance(i, dict) and i.get("label") == label) or (isinstance(i, str) and i == label) for i in data):
                continue

            # Prefer inserting near other App icons if possible (append otherwise)
            insert_idx = None
            for i, item in enumerate(data):
                if isinstance(item, dict) and item.get("icon_type") == "App":
                    insert_idx = i + 1
            if insert_idx is not None:
                data.insert(insert_idx, candela_entry)
            else:
                data.append(candela_entry)

            frappe.db.set_value("Desktop Layout", layout.name, "layout", json.dumps(data))

        frappe.db.commit()
        # Clear caches
        frappe.cache.delete_key("desktop_icons")
        frappe.cache.delete_key("bootinfo")
    except Exception:
        frappe.log_error(title="inject_app_desktop_icon: update layouts failed")


__all__ = ["inject_app_desktop_icon"]
