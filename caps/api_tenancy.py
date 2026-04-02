"""
CAPS – Multi-Tenancy API
=========================

Endpoints for managing capability configurations across multiple
Frappe sites in a multi-tenant deployment.

Features:
- Take / restore site configuration snapshots
- Compare capability configurations between sites
- Push configuration from one site profile to another
- Get a diff of two site profiles

All endpoints require System Manager or CAPS Admin role.
"""

import json
import frappe
from frappe.utils import now_datetime


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  SNAPSHOT CURRENT SITE CONFIG INTO A PROFILE                        ║
# ╚═══════════════════════════════════════════════════════════════════════╝


@frappe.whitelist()
def snapshot_site_config(profile_name: str | None = None) -> dict:
    """
    Capture the current site's CAPS configuration into a CAPS Site Profile.

    If profile_name is given, updates that profile. Otherwise creates one
    named after the current site.

    Returns the profile name and summary.
    """
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    from caps.api_transfer import export_config
    config = export_config()

    site = profile_name or frappe.local.site
    if not frappe.db.exists("CAPS Site Profile", site):
        doc = frappe.get_doc({
            "doctype": "CAPS Site Profile",
            "site_name": site,
            "site_label": site,
            "is_active": 1,
            "config_json": json.dumps(config, indent=2, default=str),
            "last_sync": now_datetime(),
        })
        doc.insert(ignore_permissions=True)
    else:
        doc = frappe.get_doc("CAPS Site Profile", site)
        doc.config_json = json.dumps(config, indent=2, default=str)
        doc.last_sync = now_datetime()
        doc.save(ignore_permissions=True)

    frappe.db.commit()
    return {
        "profile": doc.name,
        "last_sync": str(doc.last_sync),
        "summary": _config_summary(config),
    }


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  COMPARE TWO SITE PROFILES                                          ║
# ╚═══════════════════════════════════════════════════════════════════════╝


@frappe.whitelist()
def compare_site_profiles(profile_a: str, profile_b: str) -> dict:
    """
    Compare two CAPS Site Profiles and return a structured diff.

    Returns:
        {
            "summary_a": {...}, "summary_b": {...},
            "capabilities": {"only_in_a": [], "only_in_b": [], "common": []},
            "bundles": {"only_in_a": [], "only_in_b": [], "common": []},
            "field_maps": {"only_in_a": int, "only_in_b": int, "common": int},
            "action_maps": {"only_in_a": int, "only_in_b": int, "common": int},
        }
    """
    frappe.only_for(["System Manager", "CAPS Admin", "CAPS User"])
    frappe.only_for(["System Manager", "CAPS Admin", "CAPS User"])
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    config_a = _load_profile_config(profile_a)
    config_b = _load_profile_config(profile_b)

    return {
        "profile_a": profile_a,
        "profile_b": profile_b,
        "summary_a": _config_summary(config_a),
        "summary_b": _config_summary(config_b),
        "capabilities": _diff_named_list(
            config_a.get("capabilities", []),
            config_b.get("capabilities", []),
        ),
        "bundles": _diff_named_list(
            config_a.get("bundles", []),
            config_b.get("bundles", []),
        ),
        "field_maps": _diff_count(
            config_a.get("field_maps", []),
            config_b.get("field_maps", []),
        ),
        "action_maps": _diff_count(
            config_a.get("action_maps", []),
            config_b.get("action_maps", []),
        ),
    }


@frappe.whitelist()
def compare_with_current(profile_name: str) -> dict:
    """
    Compare a stored site profile against the current live configuration.

    Returns the same diff structure as compare_site_profiles.
    """
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    from caps.api_transfer import export_config
    current_config = export_config()
    stored_config = _load_profile_config(profile_name)

    return {
        "profile": profile_name,
        "vs": "current",
        "summary_stored": _config_summary(stored_config),
        "summary_current": _config_summary(current_config),
        "capabilities": _diff_named_list(
            stored_config.get("capabilities", []),
            current_config.get("capabilities", []),
        ),
        "bundles": _diff_named_list(
            stored_config.get("bundles", []),
            current_config.get("bundles", []),
        ),
        "field_maps": _diff_count(
            stored_config.get("field_maps", []),
            current_config.get("field_maps", []),
        ),
        "action_maps": _diff_count(
            stored_config.get("action_maps", []),
            current_config.get("action_maps", []),
        ),
    }


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  APPLY PROFILE TO CURRENT SITE                                      ║
# ╚═══════════════════════════════════════════════════════════════════════╝


@frappe.whitelist()
def apply_site_profile(profile_name: str, mode: str = "merge") -> dict:
    """
    Apply a stored site profile's configuration to the current site.

    Args:
        profile_name: CAPS Site Profile to apply
        mode: "merge" (skip existing) or "overwrite" (replace)

    Returns:
        import_config result dict
    """
    frappe.only_for(["System Manager"])
    frappe.only_for(["System Manager"])
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    config = _load_profile_config(profile_name)

    from caps.api_transfer import import_config
    result = import_config(data=json.dumps(config), mode=mode)
    return result


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  LIST & MANAGE PROFILES                                             ║
# ╚═══════════════════════════════════════════════════════════════════════╝


@frappe.whitelist()
def get_site_profiles() -> list[dict]:
    """Return all CAPS Site Profiles with summary info."""
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    profiles = frappe.get_all(
        "CAPS Site Profile",
        fields=["name", "site_label", "site_url", "is_active", "last_sync", "notes"],
        order_by="modified desc",
    )

    for p in profiles:
        try:
            doc = frappe.get_doc("CAPS Site Profile", p["name"])
            if doc.config_json:
                config = json.loads(doc.config_json)
                p["summary"] = _config_summary(config)
            else:
                p["summary"] = _empty_summary()
        except Exception:
            p["summary"] = _empty_summary()

    return profiles


@frappe.whitelist()
def get_profile_detail(profile_name: str) -> dict:
    """Return detailed information about a site profile."""
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    config = _load_profile_config(profile_name)
    doc = frappe.get_doc("CAPS Site Profile", profile_name)

    return {
        "name": doc.name,
        "site_label": doc.site_label,
        "site_url": doc.site_url,
        "is_active": bool(doc.is_active),
        "last_sync": str(doc.last_sync) if doc.last_sync else None,
        "notes": doc.notes,
        "summary": _config_summary(config),
        "capabilities": [c.get("name", "") for c in config.get("capabilities", [])],
        "bundles": [b.get("name", "") for b in config.get("bundles", [])],
        "field_map_count": len(config.get("field_maps", [])),
        "action_map_count": len(config.get("action_maps", [])),
        "policy_count": len(config.get("policies", [])),
        "group_count": len(config.get("groups", [])),
    }


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  HELPERS                                                             ║
# ╚═══════════════════════════════════════════════════════════════════════╝


def _load_profile_config(profile_name: str) -> dict:
    """Load and parse the config_json from a CAPS Site Profile."""
    doc = frappe.get_doc("CAPS Site Profile", profile_name)
    if not doc.config_json:
        return {}
    try:
        return json.loads(doc.config_json)
    except (json.JSONDecodeError, TypeError):
        frappe.throw(f"Invalid JSON in site profile: {profile_name}")


def _config_summary(config: dict) -> dict:
    """Summarize a config dict into counts."""
    return {
        "capabilities": len(config.get("capabilities", [])),
        "bundles": len(config.get("bundles", [])),
        "field_maps": len(config.get("field_maps", [])),
        "action_maps": len(config.get("action_maps", [])),
        "policies": len(config.get("policies", [])),
        "role_maps": len(config.get("role_maps", [])),
        "groups": len(config.get("groups", [])),
    }


def _empty_summary() -> dict:
    return {
        "capabilities": 0, "bundles": 0, "field_maps": 0,
        "action_maps": 0, "policies": 0, "role_maps": 0, "groups": 0,
    }


def _diff_named_list(list_a: list[dict], list_b: list[dict]) -> dict:
    """Diff two lists of dicts that have a 'name' key."""
    names_a = {item.get("name", "") for item in list_a}
    names_b = {item.get("name", "") for item in list_b}

    return {
        "only_in_a": sorted(names_a - names_b),
        "only_in_b": sorted(names_b - names_a),
        "common": sorted(names_a & names_b),
    }


def _diff_count(list_a: list, list_b: list) -> dict:
    """Simple count comparison for lists without stable names."""
    # Try to diff by a composite key if possible
    def _key(item):
        if isinstance(item, dict):
            parts = []
            for k in ("doctype_name", "fieldname", "action_id", "capability", "name"):
                if k in item:
                    parts.append(str(item[k]))
            return "|".join(parts)
        return str(item)

    keys_a = {_key(i) for i in list_a}
    keys_b = {_key(i) for i in list_b}

    return {
        "only_in_a": len(keys_a - keys_b),
        "only_in_b": len(keys_b - keys_a),
        "common": len(keys_a & keys_b),
    }
