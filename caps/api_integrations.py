"""
CAPS – Integration Hub API
============================

Endpoints for managing and installing pre-built capability packs
for common Frappe apps (ERPNext, HRMS, etc.).

Features:
- List available packs (built-in + custom)
- Install / uninstall packs
- Preview pack contents before installing
- Built-in packs for ERPNext, HRMS, and common Frappe patterns
"""

import json
import frappe
from frappe.utils import now_datetime


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  BUILT-IN PACKS                                                     ║
# ╚═══════════════════════════════════════════════════════════════════════╝


_BUILTIN_PACKS = {
    "erpnext_core": {
        "pack_name": "erpnext_core",
        "pack_label": "ERPNext Core",
        "app": "erpnext",
        "version": "1.0",
        "description": (
            "Core capabilities for ERPNext: sales, purchase, stock, "
            "accounting, manufacturing, and HR access control."
        ),
        "config": {
            "capabilities": [
                {"name1": "erpnext:sales:read", "label": "Sales Read", "category": "Custom"},
                {"name1": "erpnext:sales:write", "label": "Sales Write", "category": "Custom"},
                {"name1": "erpnext:sales:submit", "label": "Sales Submit", "category": "Custom"},
                {"name1": "erpnext:purchase:read", "label": "Purchase Read", "category": "Custom"},
                {"name1": "erpnext:purchase:write", "label": "Purchase Write", "category": "Custom"},
                {"name1": "erpnext:purchase:submit", "label": "Purchase Submit", "category": "Custom"},
                {"name1": "erpnext:stock:read", "label": "Stock Read", "category": "Custom"},
                {"name1": "erpnext:stock:write", "label": "Stock Write", "category": "Custom"},
                {"name1": "erpnext:accounting:read", "label": "Accounting Read", "category": "Custom"},
                {"name1": "erpnext:accounting:write", "label": "Accounting Write", "category": "Custom"},
                {"name1": "erpnext:accounting:submit", "label": "Accounting Submit", "category": "Custom"},
                {"name1": "erpnext:manufacturing:read", "label": "Manufacturing Read", "category": "Custom"},
                {"name1": "erpnext:manufacturing:write", "label": "Manufacturing Write", "category": "Custom"},
            ],
            "bundles": [
                {
                    "name": "erpnext:sales_user",
                    "bundle_label": "Sales User Bundle",
                    "items": ["erpnext:sales:read", "erpnext:sales:write"],
                },
                {
                    "name": "erpnext:sales_manager",
                    "bundle_label": "Sales Manager Bundle",
                    "items": [
                        "erpnext:sales:read", "erpnext:sales:write", "erpnext:sales:submit",
                    ],
                },
                {
                    "name": "erpnext:purchase_user",
                    "bundle_label": "Purchase User Bundle",
                    "items": ["erpnext:purchase:read", "erpnext:purchase:write"],
                },
                {
                    "name": "erpnext:accountant",
                    "bundle_label": "Accountant Bundle",
                    "items": [
                        "erpnext:accounting:read", "erpnext:accounting:write",
                        "erpnext:accounting:submit",
                    ],
                },
            ],
            "field_maps": [],
            "action_maps": [],
        },
    },
    "erpnext_sensitive": {
        "pack_name": "erpnext_sensitive",
        "pack_label": "ERPNext Sensitive Fields",
        "app": "erpnext",
        "version": "1.0",
        "description": (
            "Field-level restrictions for sensitive ERPNext data: "
            "employee salaries, customer credit limits, pricing."
        ),
        "config": {
            "capabilities": [
                {"name1": "erpnext:view_salary", "label": "View Salary Details", "category": "Custom"},
                {"name1": "erpnext:view_credit_limit", "label": "View Credit Limits", "category": "Custom"},
                {"name1": "erpnext:view_pricing", "label": "View Pricing Rules", "category": "Custom"},
                {"name1": "erpnext:view_cost_center", "label": "View Cost Centers", "category": "Custom"},
            ],
            "bundles": [],
            "field_maps": [
                {
                    "doctype_name": "Employee",
                    "fieldname": "ctc",
                    "capability": "erpnext:view_salary",
                    "behavior": "hide",
                },
                {
                    "doctype_name": "Employee",
                    "fieldname": "salary_mode",
                    "capability": "erpnext:view_salary",
                    "behavior": "hide",
                },
                {
                    "doctype_name": "Customer",
                    "fieldname": "credit_limit",
                    "capability": "erpnext:view_credit_limit",
                    "behavior": "mask",
                    "mask_pattern": "***",
                },
            ],
            "action_maps": [],
        },
    },
    "hrms_core": {
        "pack_name": "hrms_core",
        "pack_label": "HRMS Core",
        "app": "hrms",
        "version": "1.0",
        "description": (
            "Capabilities for HR Management: leave management, "
            "attendance, payroll, recruitment access control."
        ),
        "config": {
            "capabilities": [
                {"name1": "hrms:leave:read", "label": "Leave Read", "category": "Custom"},
                {"name1": "hrms:leave:approve", "label": "Leave Approve", "category": "Custom"},
                {"name1": "hrms:attendance:read", "label": "Attendance Read", "category": "Custom"},
                {"name1": "hrms:attendance:write", "label": "Attendance Write", "category": "Custom"},
                {"name1": "hrms:payroll:read", "label": "Payroll Read", "category": "Custom"},
                {"name1": "hrms:payroll:process", "label": "Payroll Process", "category": "Custom"},
                {"name1": "hrms:recruitment:read", "label": "Recruitment Read", "category": "Custom"},
                {"name1": "hrms:recruitment:write", "label": "Recruitment Write", "category": "Custom"},
            ],
            "bundles": [
                {
                    "name": "hrms:leave_manager",
                    "bundle_label": "Leave Manager Bundle",
                    "items": ["hrms:leave:read", "hrms:leave:approve"],
                },
                {
                    "name": "hrms:hr_manager",
                    "bundle_label": "HR Manager Bundle",
                    "items": [
                        "hrms:leave:read", "hrms:leave:approve",
                        "hrms:attendance:read", "hrms:attendance:write",
                        "hrms:payroll:read", "hrms:payroll:process",
                        "hrms:recruitment:read", "hrms:recruitment:write",
                    ],
                },
            ],
            "field_maps": [],
            "action_maps": [],
        },
    },
    "common_data_protection": {
        "pack_name": "common_data_protection",
        "pack_label": "Data Protection",
        "app": "frappe",
        "version": "1.0",
        "description": (
            "Common data protection capabilities: PII access, "
            "export restrictions, bulk operations, and data deletion."
        ),
        "config": {
            "capabilities": [
                {"name1": "data:view_pii", "label": "View PII Data", "category": "Custom"},
                {"name1": "data:export", "label": "Export Data", "category": "Custom"},
                {"name1": "data:bulk_delete", "label": "Bulk Delete", "category": "Custom"},
                {"name1": "data:import", "label": "Import Data", "category": "Custom"},
                {"name1": "data:print", "label": "Print Documents", "category": "Custom"},
            ],
            "bundles": [
                {
                    "name": "data:full_access",
                    "bundle_label": "Full Data Access Bundle",
                    "items": [
                        "data:view_pii", "data:export", "data:bulk_delete",
                        "data:import", "data:print",
                    ],
                },
            ],
            "field_maps": [
                {
                    "doctype_name": "User",
                    "fieldname": "phone",
                    "capability": "data:view_pii",
                    "behavior": "mask",
                    "mask_pattern": "{last4}",
                },
                {
                    "doctype_name": "User",
                    "fieldname": "mobile_no",
                    "capability": "data:view_pii",
                    "behavior": "mask",
                    "mask_pattern": "{last4}",
                },
            ],
            "action_maps": [],
        },
    },
}


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  API ENDPOINTS                                                       ║
# ╚═══════════════════════════════════════════════════════════════════════╝


@frappe.whitelist()
def get_available_packs() -> list[dict]:
    """
    List all available integration packs (built-in + custom).

    Returns list of packs with install status.
    """
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    packs = []

    # Built-in packs
    for key, pack in _BUILTIN_PACKS.items():
        installed = frappe.db.exists("CAPS Integration Pack", pack["pack_name"])
        is_installed = False
        if installed:
            doc = frappe.get_doc("CAPS Integration Pack", pack["pack_name"])
            is_installed = bool(doc.is_installed)

        config = pack["config"]
        packs.append({
            "pack_name": pack["pack_name"],
            "pack_label": pack["pack_label"],
            "app": pack["app"],
            "version": pack["version"],
            "description": pack["description"],
            "is_builtin": True,
            "is_installed": is_installed,
            "summary": {
                "capabilities": len(config.get("capabilities", [])),
                "bundles": len(config.get("bundles", [])),
                "field_maps": len(config.get("field_maps", [])),
                "action_maps": len(config.get("action_maps", [])),
            },
        })

    # Custom packs from DocType
    custom = frappe.get_all(
        "CAPS Integration Pack",
        filters={"pack_name": ("not in", list(_BUILTIN_PACKS.keys()))},
        fields=["pack_name", "pack_label", "app", "version", "description", "is_installed"],
    )
    for c in custom:
        packs.append({
            **c,
            "is_builtin": False,
            "is_installed": bool(c.get("is_installed")),
        })

    return packs


@frappe.whitelist()
def preview_pack(pack_name: str) -> dict:
    """Preview contents of a pack without installing."""
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    config = _get_pack_config(pack_name)
    return {
        "pack_name": pack_name,
        "capabilities": config.get("capabilities", []),
        "bundles": config.get("bundles", []),
        "field_maps": config.get("field_maps", []),
        "action_maps": config.get("action_maps", []),
    }


@frappe.whitelist()
def install_pack(pack_name: str) -> dict:
    """
    Install a capability integration pack.

    Creates capabilities, bundles, field maps, and action maps
    defined in the pack. Skips items that already exist.
    """
    frappe.only_for(["System Manager"])


    config = _get_pack_config(pack_name)
    results = {"created": 0, "skipped": 0, "errors": []}

    # Create capabilities
    for cap_def in config.get("capabilities", []):
        try:
            name1 = cap_def.get("name1", "")
            if frappe.db.exists("Capability", name1):
                results["skipped"] += 1
                continue
            frappe.get_doc({
                "doctype": "Capability",
                "name1": name1,
                "label": cap_def.get("label", name1),
                "category": cap_def.get("category", "Custom"),
                "is_active": 1,
            }).insert(ignore_permissions=True)
            results["created"] += 1
        except Exception as e:
            results["errors"].append({"type": "capability", "name": cap_def.get("name1"), "error": str(e)})

    # Create bundles
    for bun_def in config.get("bundles", []):
        try:
            name = bun_def.get("name", "")
            if frappe.db.exists("Capability Bundle", name):
                results["skipped"] += 1
                continue
            doc = frappe.get_doc({
                "doctype": "Capability Bundle",
                "__newname": name,
                "label": bun_def.get("bundle_label", name),
            })
            for item_name in bun_def.get("items", []):
                doc.append("capabilities", {"capability": item_name})
            doc.insert(ignore_permissions=True)
            results["created"] += 1
        except Exception as e:
            results["errors"].append({"type": "bundle", "name": bun_def.get("name"), "error": str(e)})

    # Create field maps
    for fm_def in config.get("field_maps", []):
        try:
            existing = frappe.db.exists("Field Capability Map", {
                "doctype_name": fm_def["doctype_name"],
                "fieldname": fm_def["fieldname"],
                "capability": fm_def["capability"],
            })
            if existing:
                results["skipped"] += 1
                continue
            frappe.get_doc({
                "doctype": "Field Capability Map",
                "doctype_name": fm_def["doctype_name"],
                "fieldname": fm_def["fieldname"],
                "capability": fm_def["capability"],
                "behavior": fm_def.get("behavior", "hide"),
                "mask_pattern": fm_def.get("mask_pattern", ""),
            }).insert(ignore_permissions=True)
            results["created"] += 1
        except Exception as e:
            results["errors"].append({"type": "field_map", "error": str(e)})

    # Create action maps
    for am_def in config.get("action_maps", []):
        try:
            existing = frappe.db.exists("Action Capability Map", {
                "doctype_name": am_def["doctype_name"],
                "action_id": am_def["action_id"],
                "capability": am_def["capability"],
            })
            if existing:
                results["skipped"] += 1
                continue
            frappe.get_doc({
                "doctype": "Action Capability Map",
                "doctype_name": am_def["doctype_name"],
                "action_id": am_def["action_id"],
                "action_type": am_def.get("action_type", "button"),
                "capability": am_def["capability"],
                "fallback_behavior": am_def.get("fallback_behavior", "hide"),
            }).insert(ignore_permissions=True)
            results["created"] += 1
        except Exception as e:
            results["errors"].append({"type": "action_map", "error": str(e)})

    # Record pack as installed
    _mark_pack_installed(pack_name, config)

    frappe.db.commit()
    return results


@frappe.whitelist()
def uninstall_pack(pack_name: str) -> dict:
    """
    Uninstall a capability integration pack.

    Removes capabilities, bundles, and maps created by this pack.
    Only removes items that still match the pack definition.
    """
    frappe.only_for(["System Manager"])


    config = _get_pack_config(pack_name)
    results = {"removed": 0, "skipped": 0, "errors": []}

    # Remove action maps first (depend on capabilities)
    for am_def in config.get("action_maps", []):
        try:
            existing = frappe.db.exists("Action Capability Map", {
                "doctype_name": am_def["doctype_name"],
                "action_id": am_def["action_id"],
                "capability": am_def["capability"],
            })
            if existing:
                frappe.delete_doc("Action Capability Map", existing, force=True, ignore_permissions=True)
                results["removed"] += 1
            else:
                results["skipped"] += 1
        except Exception as e:
            results["errors"].append({"type": "action_map", "error": str(e)})

    # Remove field maps
    for fm_def in config.get("field_maps", []):
        try:
            existing = frappe.db.exists("Field Capability Map", {
                "doctype_name": fm_def["doctype_name"],
                "fieldname": fm_def["fieldname"],
                "capability": fm_def["capability"],
            })
            if existing:
                frappe.delete_doc("Field Capability Map", existing, force=True, ignore_permissions=True)
                results["removed"] += 1
            else:
                results["skipped"] += 1
        except Exception as e:
            results["errors"].append({"type": "field_map", "error": str(e)})

    # Remove bundles
    for bun_def in config.get("bundles", []):
        try:
            name = bun_def.get("name", "")
            if frappe.db.exists("Capability Bundle", name):
                frappe.delete_doc("Capability Bundle", name, force=True, ignore_permissions=True)
                results["removed"] += 1
            else:
                results["skipped"] += 1
        except Exception as e:
            results["errors"].append({"type": "bundle", "error": str(e)})

    # Remove capabilities
    for cap_def in config.get("capabilities", []):
        try:
            name1 = cap_def.get("name1", "")
            if frappe.db.exists("Capability", name1):
                frappe.delete_doc("Capability", name1, force=True, ignore_permissions=True)
                results["removed"] += 1
            else:
                results["skipped"] += 1
        except Exception as e:
            results["errors"].append({"type": "capability", "error": str(e)})

    # Mark as uninstalled
    if frappe.db.exists("CAPS Integration Pack", pack_name):
        doc = frappe.get_doc("CAPS Integration Pack", pack_name)
        doc.is_installed = 0
        doc.save(ignore_permissions=True)

    frappe.db.commit()
    return results


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  HELPERS                                                             ║
# ╚═══════════════════════════════════════════════════════════════════════╝


def _get_pack_config(pack_name: str) -> dict:
    """Get the config dict for a pack (built-in or custom)."""
    # Check built-in first
    if pack_name in _BUILTIN_PACKS:
        return _BUILTIN_PACKS[pack_name]["config"]

    # Check custom pack
    if frappe.db.exists("CAPS Integration Pack", pack_name):
        doc = frappe.get_doc("CAPS Integration Pack", pack_name)
        if doc.config_json:
            try:
                return json.loads(doc.config_json)
            except (json.JSONDecodeError, TypeError):
                pass

    frappe.throw(f"Integration pack not found: {pack_name}")


def _mark_pack_installed(pack_name: str, config: dict):
    """Create or update the CAPS Integration Pack record."""
    meta = _BUILTIN_PACKS.get(pack_name, {})

    if not frappe.db.exists("CAPS Integration Pack", pack_name):
        frappe.get_doc({
            "doctype": "CAPS Integration Pack",
            "pack_name": pack_name,
            "pack_label": meta.get("pack_label", pack_name),
            "app": meta.get("app", ""),
            "version": meta.get("version", "1.0"),
            "description": meta.get("description", ""),
            "is_installed": 1,
            "config_json": json.dumps(config, indent=2, default=str),
        }).insert(ignore_permissions=True)
    else:
        doc = frappe.get_doc("CAPS Integration Pack", pack_name)
        doc.is_installed = 1
        doc.config_json = json.dumps(config, indent=2, default=str)
        doc.save(ignore_permissions=True)
