"""
CAPS Audit Report
=================

Filterable audit log report showing capability checks, grants, revokes,
policy applications, and delegation events.

Supports date range, user, action type, capability, and result filters.
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
            "label": _("Timestamp"),
            "fieldtype": "Datetime",
            "fieldname": "timestamp",
            "width": 170,
        },
        {
            "label": _("User"),
            "fieldtype": "Link",
            "fieldname": "user",
            "options": "User",
            "width": 180,
        },
        {
            "label": _("Action"),
            "fieldtype": "Data",
            "fieldname": "action",
            "width": 150,
        },
        {
            "label": _("Capability"),
            "fieldtype": "Link",
            "fieldname": "capability",
            "options": "Capability",
            "width": 200,
        },
        {
            "label": _("Result"),
            "fieldtype": "Data",
            "fieldname": "result",
            "width": 100,
        },
        {
            "label": _("Context"),
            "fieldtype": "Small Text",
            "fieldname": "context",
            "width": 250,
        },
        {
            "label": _("IP Address"),
            "fieldtype": "Data",
            "fieldname": "ip_address",
            "width": 130,
        },
        {
            "label": _("Audit Log"),
            "fieldtype": "Link",
            "fieldname": "name",
            "options": "CAPS Audit Log",
            "width": 150,
        },
    ]


def get_data(filters):
    conditions = {}

    if filters.get("user"):
        conditions["user"] = filters["user"]
    if filters.get("action"):
        conditions["action"] = filters["action"]
    if filters.get("capability"):
        conditions["capability"] = filters["capability"]
    if filters.get("result"):
        conditions["result"] = filters["result"]

    # Date range
    if filters.get("from_date"):
        conditions["timestamp"] = (">=", filters["from_date"])
    if filters.get("to_date"):
        if "timestamp" in conditions:
            # Already have a >= condition, switch to between
            conditions["timestamp"] = (
                "between",
                [filters.get("from_date") or "2000-01-01", filters["to_date"] + " 23:59:59"],
            )
        else:
            conditions["timestamp"] = ("<=", filters["to_date"] + " 23:59:59")

    data = frappe.get_all(
        "CAPS Audit Log",
        filters=conditions,
        fields=[
            "name", "timestamp", "user", "action", "capability",
            "result", "context", "ip_address",
        ],
        order_by="timestamp desc",
        limit_page_length=500,
    )

    return data
