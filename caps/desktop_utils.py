"""
Reusable helpers for Desktop Icon injection on Frappe v16 /desk.

Usage (inside after_install):
    from <your_app>.desktop_utils import inject_app_desktop_icon
    inject_app_desktop_icon(
        app="your_app",
        label="Your App",
        route="/desk/your-app",
        logo_url="/assets/your_app/images/logo.svg",
        bg_color="#6366F1",
    )
"""

import json
import frappe


def inject_app_desktop_icon(
    app: str,
    label: str,
    route: str,
    logo_url: str,
    bg_color: str = "blue",
):
    """Create Desktop Icon and inject it into every Desktop Layout.

    Safe to call multiple times (idempotent).
    """
    # 1. Create the Desktop Icon record ─────────────────────────
    try:
        if not frappe.db.exists("DocType", "Desktop Icon"):
            return

        existing = frappe.db.get_value(
            "Desktop Icon", {"app": app, "icon_type": "App"}, "name"
        )
        if not existing:
            existing = frappe.db.get_value(
                "Desktop Icon", {"label": label, "icon_type": "App"}, "name"
            )

        if not existing:
            frappe.get_doc({
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
            }).insert(ignore_permissions=True)
            frappe.db.commit()
    except Exception:
        frappe.log_error(title=f"inject_app_desktop_icon({app}): create icon failed")

    # 2. Inject into every Desktop Layout ────────────────────────
    try:
        if not frappe.db.exists("DocType", "Desktop Layout"):
            return

        icon_entry = {
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

            already = any(
                (isinstance(i, dict) and i.get("label") == label)
                or (isinstance(i, str) and i == label)
                for i in data
            )
            if already:
                continue

            # Insert after last App-type icon if possible
            insert_idx = None
            for idx, item in enumerate(data):
                if isinstance(item, dict) and item.get("icon_type") == "App":
                    insert_idx = idx + 1
            if insert_idx is not None:
                data.insert(insert_idx, icon_entry)
            else:
                data.append(icon_entry)

            frappe.db.set_value(
                "Desktop Layout", layout.name, "layout", json.dumps(data)
            )

        frappe.db.commit()
        frappe.cache.delete_key("desktop_icons")
        frappe.cache.delete_key("bootinfo")
    except Exception:
        frappe.log_error(title=f"inject_app_desktop_icon({app}): update layouts failed")


__all__ = ["inject_app_desktop_icon"]
