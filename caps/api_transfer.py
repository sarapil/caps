# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS – Configuration Import / Export
======================================

Endpoints for exporting and importing CAPS configuration as JSON.
Used for environment portability (dev → staging → production),
backups, and auditing.

Exportable entities:
  - Capabilities (with prerequisites)
  - Capability Bundles (with items)
  - Role Capability Maps (with items + bundles)
  - Field Capability Maps
  - Action Capability Maps
  - Capability Policies
  - Permission Groups (structure only, not members)

All endpoints require CAPS Admin or System Manager role.
"""

import json
import frappe
from frappe.utils import now_datetime


_EXPORT_VERSION = 1


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  EXPORT                                                              ║
# ╚═══════════════════════════════════════════════════════════════════════╝


@frappe.whitelist()
def export_config(
    include_capabilities: bool = True,
    include_bundles: bool = True,
    include_role_maps: bool = True,
    include_field_maps: bool = True,
    include_action_maps: bool = True,
    include_policies: bool = True,
    include_groups: bool = True,
) -> dict:
    frappe.only_for(["System Manager"])
    """
    Export CAPS configuration as a JSON-serialisable dict.

    Each flag controls whether a category is included. Returns a
    complete package that can be fed back into import_config().
    """
    frappe.only_for(["System Manager", "CAPS Admin"])

    # Normalise bool strings from web calls
    flags = {
        "capabilities": _to_bool(include_capabilities),
        "bundles": _to_bool(include_bundles),
        "role_maps": _to_bool(include_role_maps),
        "field_maps": _to_bool(include_field_maps),
        "action_maps": _to_bool(include_action_maps),
        "policies": _to_bool(include_policies),
        "groups": _to_bool(include_groups),
    }

    package = {
        "caps_export_version": _EXPORT_VERSION,
        "exported_at": str(now_datetime()),
        "exported_by": frappe.session.user,
        "site": frappe.local.site,
    }

    if flags["capabilities"]:
        package["capabilities"] = _export_capabilities()

    if flags["bundles"]:
        package["bundles"] = _export_bundles()

    if flags["role_maps"]:
        package["role_maps"] = _export_role_maps()

    if flags["field_maps"]:
        package["field_maps"] = _export_field_maps()

    if flags["action_maps"]:
        package["action_maps"] = _export_action_maps()

    if flags["policies"]:
        package["policies"] = _export_policies()

    if flags["groups"]:
        package["groups"] = _export_groups()

    return package


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  IMPORT                                                              ║
# ╚═══════════════════════════════════════════════════════════════════════╝


@frappe.whitelist()
def import_config(config: str | dict, mode: str = "merge") -> dict:
    """
    Import CAPS configuration from a previously exported package.

    Args:
        config: JSON string or dict (the export package)
        mode: "merge" (skip existing) or "overwrite" (update existing)

    Returns:
        {created: int, updated: int, skipped: int, errors: [...]}
    """
    frappe.only_for(["System Manager", "CAPS Admin"])

    if isinstance(config, str):
        config = json.loads(config)

    if config.get("caps_export_version", 0) > _EXPORT_VERSION:
        frappe.throw("Export version is newer than this CAPS version supports")

    if mode not in ("merge", "overwrite"):
        frappe.throw("Mode must be 'merge' or 'overwrite'")

    result = {"created": 0, "updated": 0, "skipped": 0, "errors": []}

    # Import order matters: capabilities first (they're referenced by others)
    if "capabilities" in config:
        _import_capabilities(config["capabilities"], mode, result)

    if "bundles" in config:
        _import_bundles(config["bundles"], mode, result)

    if "role_maps" in config:
        _import_role_maps(config["role_maps"], mode, result)

    if "field_maps" in config:
        _import_field_maps(config["field_maps"], mode, result)

    if "action_maps" in config:
        _import_action_maps(config["action_maps"], mode, result)

    if "policies" in config:
        _import_policies(config["policies"], mode, result)

    if "groups" in config:
        _import_groups(config["groups"], mode, result)

    frappe.db.commit()

    # Bust all caches
    _bust_all_caches()

    return result


@frappe.whitelist()
def validate_import(config: str | dict) -> dict:
    """
    Dry-run validation: report what would be created/updated/skipped
    without making changes.
    """
    frappe.only_for(["System Manager", "CAPS Admin"])

    if isinstance(config, str):
        config = json.loads(config)

    report = {
        "version_ok": config.get("caps_export_version", 0) <= _EXPORT_VERSION,
        "sections": {},
    }

    for section in ("capabilities", "bundles", "role_maps", "field_maps",
                     "action_maps", "policies", "groups"):
        items = config.get(section, [])
        if not items:
            continue

        existing = 0
        new = 0
        for item in items:
            name = item.get("name") or item.get("name1") or item.get("policy_name")
            if name and _entity_exists(section, name):
                existing += 1
            else:
                new += 1

        report["sections"][section] = {
            "total": len(items),
            "new": new,
            "existing": existing,
        }

    return report


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  EXPORT HELPERS                                                      ║
# ╚═══════════════════════════════════════════════════════════════════════╝


def _export_capabilities():
    caps = frappe.get_all(
        "Capability",
        fields=["name", "name1", "label", "category", "description",
                "is_active", "is_delegatable"],
    )
    for cap in caps:
        # Include prerequisites
        prereqs = frappe.get_all(
            "Capability Prerequisite",
            filters={"parent": cap["name"], "parenttype": "Capability"},
            fields=["prerequisite", "is_hard"],
        )
        cap["prerequisites"] = prereqs
    return caps


def _export_bundles():
    bundles = frappe.get_all(
        "Capability Bundle",
        fields=["name", "label", "description"],
    )
    for b in bundles:
        items = frappe.get_all(
            "Capability Bundle Item",
            filters={"parent": b["name"]},
            fields=["capability"],
        )
        b["items"] = [i["capability"] for i in items]
    return bundles


def _export_role_maps():
    maps = frappe.get_all(
        "Role Capability Map",
        fields=["name", "role"],
    )
    for m in maps:
        items = frappe.get_all(
            "Role Capability Item",
            filters={"parent": m["name"]},
            fields=["capability"],
        )
        m["capabilities"] = [i["capability"] for i in items]

        bundles = frappe.get_all(
            "Role Capability Bundle",
            filters={"parent": m["name"]},
            fields=["bundle"],
        )
        m["bundles"] = [b["bundle"] for b in bundles]
    return maps


def _export_field_maps():
    return frappe.get_all(
        "Field Capability Map",
        fields=["name", "doctype_name", "fieldname", "capability",
                "behavior", "mask_pattern", "custom_handler"],
    )


def _export_action_maps():
    return frappe.get_all(
        "Action Capability Map",
        fields=["name", "doctype_name", "action_id", "action_type",
                "capability", "fallback_behavior", "fallback_message"],
    )


def _export_policies():
    policies = frappe.get_all(
        "Capability Policy",
        fields=["name", "policy_name", "target_type", "target_role",
                "target_department", "target_users", "grant_type",
                "capability", "bundle", "starts_on", "ends_on",
                "is_active", "priority", "description"],
    )
    # Convert datetimes to strings
    for p in policies:
        for dt_field in ("starts_on", "ends_on"):
            if p.get(dt_field):
                p[dt_field] = str(p[dt_field])
    return policies


def _export_groups():
    groups = frappe.get_all(
        "Permission Group",
        fields=["name", "group_type", "auto_sync", "sync_source", "sync_query"],
    )
    for g in groups:
        caps = frappe.get_all(
            "Permission Group Capability",
            filters={"parent": g["name"]},
            fields=["capability"],
        )
        g["capabilities"] = [c["capability"] for c in caps]

        bundles = frappe.get_all(
            "Permission Group Bundle",
            filters={"parent": g["name"]},
            fields=["bundle"],
        )
        g["bundles"] = [b["bundle"] for b in bundles]
    return groups


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  IMPORT HELPERS                                                      ║
# ╚═══════════════════════════════════════════════════════════════════════╝


def _import_capabilities(items, mode, result):
    for item in items:
        try:
            name = item.get("name1") or item.get("name")
            exists = frappe.db.exists("Capability", name)

            if exists and mode == "merge":
                result["skipped"] += 1
                continue

            if exists and mode == "overwrite":
                doc = frappe.get_doc("Capability", name)
                doc.label = item.get("label", name)
                doc.category = item.get("category", "Custom")
                doc.description = item.get("description")
                doc.is_active = item.get("is_active", 1)
                doc.is_delegatable = item.get("is_delegatable", 0)
                # Update prerequisites
                doc.prerequisites = []
                for p in item.get("prerequisites", []):
                    doc.append("prerequisites", {
                        "prerequisite": p.get("prerequisite"),
                        "is_hard": p.get("is_hard", 1),
                    })
                doc.save(ignore_permissions=True)
                result["updated"] += 1
            else:
                doc = frappe.get_doc({
                    "doctype": "Capability",
                    "name1": name,
                    "label": item.get("label", name),
                    "category": item.get("category", "Custom"),
                    "description": item.get("description"),
                    "is_active": item.get("is_active", 1),
                    "is_delegatable": item.get("is_delegatable", 0),
                })
                for p in item.get("prerequisites", []):
                    doc.append("prerequisites", {
                        "prerequisite": p.get("prerequisite"),
                        "is_hard": p.get("is_hard", 1),
                    })
                doc.insert(ignore_permissions=True)
                result["created"] += 1
        except Exception as e:
            result["errors"].append({"type": "capability", "name": item.get("name"), "error": str(e)})


def _import_bundles(items, mode, result):
    for item in items:
        try:
            name = item.get("name")
            exists = frappe.db.exists("Capability Bundle", name)

            if exists and mode == "merge":
                result["skipped"] += 1
                continue

            if exists and mode == "overwrite":
                doc = frappe.get_doc("Capability Bundle", name)
                doc.description = item.get("description")
                doc.capabilities = []
                for cap in item.get("items", []):
                    doc.append("capabilities", {"capability": cap})
                doc.save(ignore_permissions=True)
                result["updated"] += 1
            else:
                doc = frappe.get_doc({
                    "doctype": "Capability Bundle",
                    "__newname": name,
                    "label": item.get("label", name),
                    "description": item.get("description"),
                })
                for cap in item.get("items", []):
                    doc.append("capabilities", {"capability": cap})
                doc.insert(ignore_permissions=True)
                result["created"] += 1
        except Exception as e:
            result["errors"].append({"type": "bundle", "name": item.get("name"), "error": str(e)})


def _import_role_maps(items, mode, result):
    for item in items:
        try:
            role = item.get("role")
            name = frappe.db.get_value("Role Capability Map", {"role": role}, "name")

            if name and mode == "merge":
                result["skipped"] += 1
                continue

            if name and mode == "overwrite":
                doc = frappe.get_doc("Role Capability Map", name)
                doc.role_capabilities = []
                for cap in item.get("capabilities", []):
                    doc.append("role_capabilities", {"capability": cap})
                doc.role_bundles = []
                for b in item.get("bundles", []):
                    doc.append("role_bundles", {"bundle": b})
                doc.save(ignore_permissions=True)
                result["updated"] += 1
            else:
                doc = frappe.get_doc({
                    "doctype": "Role Capability Map",
                    "role": role,
                })
                for cap in item.get("capabilities", []):
                    doc.append("role_capabilities", {"capability": cap})
                for b in item.get("bundles", []):
                    doc.append("role_bundles", {"bundle": b})
                doc.insert(ignore_permissions=True)
                result["created"] += 1
        except Exception as e:
            result["errors"].append({"type": "role_map", "name": item.get("role"), "error": str(e)})


def _import_field_maps(items, mode, result):
    for item in items:
        try:
            # Field maps are identified by doctype + field + capability
            exists = frappe.db.exists("Field Capability Map", {
                "doctype_name": item.get("doctype_name"),
                "fieldname": item.get("fieldname"),
                "capability": item.get("capability"),
            })

            if exists and mode == "merge":
                result["skipped"] += 1
                continue

            if exists and mode == "overwrite":
                doc = frappe.get_doc("Field Capability Map", exists)
                doc.behavior = item.get("behavior", "hide")
                doc.mask_pattern = item.get("mask_pattern")
                doc.custom_handler = item.get("custom_handler")
                doc.save(ignore_permissions=True)
                result["updated"] += 1
            else:
                frappe.get_doc({
                    "doctype": "Field Capability Map",
                    "doctype_name": item.get("doctype_name"),
                    "fieldname": item.get("fieldname"),
                    "capability": item.get("capability"),
                    "behavior": item.get("behavior", "hide"),
                    "mask_pattern": item.get("mask_pattern"),
                    "custom_handler": item.get("custom_handler"),
                }).insert(ignore_permissions=True)
                result["created"] += 1
        except Exception as e:
            result["errors"].append({"type": "field_map", "name": item.get("fieldname"), "error": str(e)})


def _import_action_maps(items, mode, result):
    for item in items:
        try:
            exists = frappe.db.exists("Action Capability Map", {
                "doctype_name": item.get("doctype_name"),
                "action_id": item.get("action_id"),
                "capability": item.get("capability"),
            })

            if exists and mode == "merge":
                result["skipped"] += 1
                continue

            if exists and mode == "overwrite":
                doc = frappe.get_doc("Action Capability Map", exists)
                doc.action_type = item.get("action_type", "button")
                doc.fallback_behavior = item.get("fallback_behavior", "hide")
                doc.fallback_message = item.get("fallback_message")
                doc.save(ignore_permissions=True)
                result["updated"] += 1
            else:
                frappe.get_doc({
                    "doctype": "Action Capability Map",
                    "doctype_name": item.get("doctype_name"),
                    "action_id": item.get("action_id"),
                    "action_type": item.get("action_type", "button"),
                    "capability": item.get("capability"),
                    "fallback_behavior": item.get("fallback_behavior", "hide"),
                    "fallback_message": item.get("fallback_message"),
                }).insert(ignore_permissions=True)
                result["created"] += 1
        except Exception as e:
            result["errors"].append({"type": "action_map", "name": item.get("action_id"), "error": str(e)})


def _import_policies(items, mode, result):
    for item in items:
        try:
            name = item.get("policy_name") or item.get("name")
            exists = frappe.db.exists("Capability Policy", name)

            if exists and mode == "merge":
                result["skipped"] += 1
                continue

            if exists and mode == "overwrite":
                doc = frappe.get_doc("Capability Policy", name)
                for field in ("target_type", "target_role", "target_department",
                              "target_users", "grant_type", "capability", "bundle",
                              "starts_on", "ends_on", "is_active", "priority", "description"):
                    if field in item:
                        setattr(doc, field, item[field])
                doc.save(ignore_permissions=True)
                result["updated"] += 1
            else:
                doc_data = {
                    "doctype": "Capability Policy",
                    "policy_name": name,
                }
                for field in ("target_type", "target_role", "target_department",
                              "target_users", "grant_type", "capability", "bundle",
                              "starts_on", "ends_on", "is_active", "priority", "description"):
                    if field in item:
                        doc_data[field] = item[field]
                frappe.get_doc(doc_data).insert(ignore_permissions=True)
                result["created"] += 1
        except Exception as e:
            result["errors"].append({"type": "policy", "name": item.get("policy_name"), "error": str(e)})


def _import_groups(items, mode, result):
    for item in items:
        try:
            name = item.get("name")
            exists = frappe.db.exists("Permission Group", name)

            if exists and mode == "merge":
                result["skipped"] += 1
                continue

            if exists and mode == "overwrite":
                doc = frappe.get_doc("Permission Group", name)
                doc.group_type = item.get("group_type", "Manual")
                doc.auto_sync = item.get("auto_sync", 0)
                doc.sync_source = item.get("sync_source")
                doc.sync_query = item.get("sync_query")
                doc.group_capabilities = []
                for cap in item.get("capabilities", []):
                    doc.append("group_capabilities", {"capability": cap})
                doc.group_bundles = []
                for b in item.get("bundles", []):
                    doc.append("group_bundles", {"bundle": b})
                doc.save(ignore_permissions=True)
                result["updated"] += 1
            else:
                doc = frappe.get_doc({
                    "doctype": "Permission Group",
                    "__newname": name,
                    "label": item.get("label", name),
                    "group_type": item.get("group_type", "Manual"),
                    "auto_sync": item.get("auto_sync", 0),
                    "sync_source": item.get("sync_source"),
                    "sync_query": item.get("sync_query"),
                })
                for cap in item.get("capabilities", []):
                    doc.append("group_capabilities", {"capability": cap})
                for b in item.get("bundles", []):
                    doc.append("group_bundles", {"bundle": b})
                doc.insert(ignore_permissions=True)
                result["created"] += 1
        except Exception as e:
            result["errors"].append({"type": "group", "name": item.get("name"), "error": str(e)})


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  UTILITIES                                                           ║
# ╚═══════════════════════════════════════════════════════════════════════╝


def _to_bool(val):
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes")
    return bool(val)


def _entity_exists(section, name):
    """Check if an entity exists in the database by section type."""
    dt_map = {
        "capabilities": "Capability",
        "bundles": "Capability Bundle",
        "role_maps": "Role Capability Map",
        "field_maps": "Field Capability Map",
        "action_maps": "Action Capability Map",
        "policies": "Capability Policy",
        "groups": "Permission Group",
    }
    dt = dt_map.get(section)
    if not dt:
        return False
    return frappe.db.exists(dt, name)


def _bust_all_caches():
    """Clear all CAPS caches after import."""
    from caps.utils.resolver import invalidate_all_caches, invalidate_field_action_caches
    invalidate_all_caches()
    invalidate_field_action_caches()
    frappe.cache.delete_value("caps:prereq_map")
    frappe.cache.delete_value("caps:hierarchy_map")
    invalidate_field_action_caches()
