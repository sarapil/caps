# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""CAPS — Boot session hook.

Injects a lightweight capability summary into the user's session so the
client-side ``frappe.caps`` object can enforce field/action restrictions
without an extra round-trip on every form load.
"""

import frappe


def boot_session(bootinfo):
    """Called by Frappe during session boot."""
    if frappe.session.user == "Guest":
        return

    from caps.utils.resolver import (
        get_action_restrictions_all,
        get_field_restrictions_all,
        resolve_capabilities,
    )

    try:
        caps = resolve_capabilities(frappe.session.user)
        bootinfo["caps"] = {
            "capabilities": list(caps),
            "field_restrictions": get_field_restrictions_all(frappe.session.user),
            "action_restrictions": get_action_restrictions_all(frappe.session.user),
            "version": _get_caps_version(),
        }

        # Impersonation status
        try:
            from caps.api_impersonation import get_impersonation_state
            imp = get_impersonation_state(frappe.session.user)
            if imp:
                bootinfo["caps"]["impersonating"] = imp["target_user"]
        except Exception:
            pass
    except Exception:
        # Never break the boot for CAPS errors
        bootinfo["caps"] = {
            "capabilities": [],
            "field_restrictions": {},
            "action_restrictions": {},
            "version": 0,
        }


def _get_caps_version():
    """Return a monotonic version counter bumped on every Field/Action map change."""
    return int(frappe.cache.get_value("caps:map_version") or 0)
