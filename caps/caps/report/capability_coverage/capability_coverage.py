"""
Capability Coverage Report
==========================

Shows which capabilities are configured and how they are assigned:
- How many users have each capability (direct, group, role)
- Which DocTypes have Field/Action maps
- Bundle membership

Helps admins identify uncovered or over-provisioned capabilities.
"""

import frappe
from frappe import _


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "label": _("Capability"),
            "fieldtype": "Link",
            "fieldname": "capability",
            "options": "Capability",
            "width": 220,
        },
        {
            "label": _("Label"),
            "fieldtype": "Data",
            "fieldname": "label",
            "width": 200,
        },
        {
            "label": _("Active"),
            "fieldtype": "Check",
            "fieldname": "is_active",
            "width": 70,
        },
        {
            "label": _("Direct Users"),
            "fieldtype": "Int",
            "fieldname": "direct_users",
            "width": 110,
        },
        {
            "label": _("Group Users"),
            "fieldtype": "Int",
            "fieldname": "group_users",
            "width": 110,
        },
        {
            "label": _("Role Maps"),
            "fieldtype": "Int",
            "fieldname": "role_maps",
            "width": 100,
        },
        {
            "label": _("Bundles"),
            "fieldtype": "Int",
            "fieldname": "bundles",
            "width": 90,
        },
        {
            "label": _("Field Maps"),
            "fieldtype": "Int",
            "fieldname": "field_maps",
            "width": 100,
        },
        {
            "label": _("Action Maps"),
            "fieldtype": "Int",
            "fieldname": "action_maps",
            "width": 100,
        },
        {
            "label": _("Total Coverage"),
            "fieldtype": "Int",
            "fieldname": "total_coverage",
            "width": 120,
        },
    ]


def get_data(filters):
    conditions = {}
    if filters.get("is_active"):
        conditions["is_active"] = 1
    if filters.get("category"):
        conditions["category"] = filters["category"]

    capabilities = frappe.get_all(
        "Capability",
        filters=conditions,
        fields=["name", "label", "is_active"],
        order_by="name",
    )

    if not capabilities:
        return []

    cap_names = [c["name"] for c in capabilities]

    # Direct user assignments
    direct_counts = _count_grouped("User Capability Item", "capability", cap_names)

    # Group assignments
    group_counts = _count_grouped("Permission Group Capability", "capability", cap_names)

    # Role map assignments
    role_counts = _count_grouped("Role Capability Item", "capability", cap_names)

    # Bundle memberships
    bundle_counts = _count_grouped("Capability Bundle Item", "capability", cap_names)

    # Field Capability Maps
    field_map_counts = _count_grouped("Field Capability Map", "capability", cap_names)

    # Action Capability Maps
    action_map_counts = _count_grouped("Action Capability Map", "capability", cap_names)

    data = []
    for cap in capabilities:
        name = cap["name"]
        direct = direct_counts.get(name, 0)
        group = group_counts.get(name, 0)
        role = role_counts.get(name, 0)
        bundles = bundle_counts.get(name, 0)
        field_maps = field_map_counts.get(name, 0)
        action_maps = action_map_counts.get(name, 0)

        data.append({
            "capability": name,
            "label": cap["label"],
            "is_active": cap["is_active"],
            "direct_users": direct,
            "group_users": group,
            "role_maps": role,
            "bundles": bundles,
            "field_maps": field_maps,
            "action_maps": action_maps,
            "total_coverage": direct + group + role,
        })

    return data


def _count_grouped(doctype: str, field: str, values: list) -> dict:
    """Count occurrences grouped by field value."""
    if not values:
        return {}

    placeholders = ", ".join(["%s"] * len(values))
    table = f"tab{doctype}"
    rows = frappe.db.sql(
        f"SELECT `{field}` as grp, COUNT(name) as cnt FROM `{table}` WHERE `{field}` IN ({placeholders}) GROUP BY `{field}`",
        values,
        as_dict=True,
    )
    return {r["grp"]: r["cnt"] for r in rows}
