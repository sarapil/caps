# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS – Analytics Dashboard API
Endpoints returning aggregate stats, charts, and forecasts
for the CAPS admin dashboard.
"""

import frappe
from frappe.utils import now_datetime, add_days, getdate


@frappe.whitelist()
def get_dashboard_stats():
    """Return summary numbers for the CAPS dashboard."""
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    total_capabilities = frappe.db.count("Capability")
    active_capabilities = frappe.db.count("Capability", {"is_active": 1})
    total_bundles = frappe.db.count("Capability Bundle")
    total_groups = frappe.db.count("Permission Group")

    # Users with at least one direct capability
    users_with_caps = frappe.db.sql("""
        SELECT COUNT(DISTINCT uc.user)
        FROM `tabUser Capability` uc
        INNER JOIN `tabUser Capability Item` uci ON uci.parent = uc.name
    """)[0][0] or 0

    # Total direct grants
    total_grants = frappe.db.count("User Capability Item")

    # Pending requests
    pending_requests = frappe.db.count("Capability Request", {"status": "Pending"})

    # Active policies
    active_policies = frappe.db.count("Capability Policy", {"is_active": 1})

    # Expiring soon (next 7 days)
    week_from_now = add_days(now_datetime(), 7)
    expiring_soon = frappe.db.count(
        "User Capability Item",
        {
            "expires_on": ["between", [now_datetime(), week_from_now]],
        },
    )

    # Delegated grants
    delegated_count = frappe.db.sql("""
        SELECT COUNT(*) FROM `tabUser Capability Item`
        WHERE delegated_by IS NOT NULL AND delegated_by != ''
    """)[0][0] or 0

    return {
        "total_capabilities": total_capabilities,
        "active_capabilities": active_capabilities,
        "total_bundles": total_bundles,
        "total_groups": total_groups,
        "users_with_capabilities": users_with_caps,
        "total_grants": total_grants,
        "pending_requests": pending_requests,
        "active_policies": active_policies,
        "expiring_soon": expiring_soon,
        "delegated_grants": delegated_count,
    }


@frappe.whitelist()
def get_capability_distribution():
    """Chart data: how many users hold each capability (top 20)."""
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    data = frappe.db.sql("""
        SELECT uci.capability, COUNT(*) as user_count
        FROM `tabUser Capability Item` uci
        GROUP BY uci.capability
        ORDER BY user_count DESC
        LIMIT 20
    """, as_dict=True)

    return {
        "labels": [d.capability for d in data],
        "datasets": [{
            "name": "Users",
            "values": [d.user_count for d in data],
        }],
    }


@frappe.whitelist()
def get_audit_timeline(days=30):
    """Chart data: audit log activity grouped by day."""
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    days = int(days)
    start_date = add_days(getdate(), -days)

    data = frappe.db.sql("""
        SELECT DATE(creation) as log_date, action, COUNT(*) as count
        FROM `tabCAPS Audit Log`
        WHERE DATE(creation) >= %(start_date)s
        GROUP BY DATE(creation), action
        ORDER BY log_date ASC
    """, {"start_date": start_date}, as_dict=True)

    # Pivot: date → {action: count}
    from collections import OrderedDict
    dates = OrderedDict()
    actions_set = set()

    for row in data:
        d = str(row.log_date)
        if d not in dates:
            dates[d] = {}
        dates[d][row.action] = row.count
        actions_set.add(row.action)

    actions_list = sorted(actions_set)
    labels = list(dates.keys())
    datasets = []

    for action in actions_list:
        datasets.append({
            "name": action,
            "values": [dates.get(d, {}).get(action, 0) for d in labels],
        })

    return {"labels": labels, "datasets": datasets}


@frappe.whitelist()
def get_expiry_forecast(days=30):
    """Chart data: capability grants expiring in the next N days, grouped by day."""
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    days = int(days)
    current = now_datetime()
    end_date = add_days(current, days)

    data = frappe.db.sql("""
        SELECT DATE(uci.expires_on) as expiry_date,
               COUNT(*) as count
        FROM `tabUser Capability Item` uci
        WHERE uci.expires_on BETWEEN %(start)s AND %(end)s
        GROUP BY DATE(uci.expires_on)
        ORDER BY expiry_date ASC
    """, {"start": current, "end": end_date}, as_dict=True)

    return {
        "labels": [str(d.expiry_date) for d in data],
        "datasets": [{
            "name": "Expiring Grants",
            "values": [d.count for d in data],
        }],
    }


@frappe.whitelist()
def get_request_summary():
    """Breakdown of capability requests by status."""
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    data = frappe.db.sql("""
        SELECT status, COUNT(*) as count
        FROM `tabCapability Request`
        GROUP BY status
    """, as_dict=True)

    return {
        "labels": [d.status for d in data],
        "datasets": [{
            "name": "Requests",
            "values": [d.count for d in data],
        }],
    }


@frappe.whitelist()
def get_delegation_summary():
    """Summary of delegation activity."""
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    # Top delegators
    top_delegators = frappe.db.sql("""
        SELECT delegated_by, COUNT(*) as count
        FROM `tabUser Capability Item`
        WHERE delegated_by IS NOT NULL AND delegated_by != ''
        GROUP BY delegated_by
        ORDER BY count DESC
        LIMIT 10
    """, as_dict=True)

    # Most delegated capabilities
    top_caps = frappe.db.sql("""
        SELECT capability, COUNT(*) as count
        FROM `tabUser Capability Item`
        WHERE delegated_by IS NOT NULL AND delegated_by != ''
        GROUP BY capability
        ORDER BY count DESC
        LIMIT 10
    """, as_dict=True)

    return {
        "top_delegators": top_delegators,
        "top_delegated_capabilities": top_caps,
    }


@frappe.whitelist()
def get_policy_summary():
    """Summary of policy status and impact."""
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    active = frappe.db.count("Capability Policy", {"is_active": 1})
    inactive = frappe.db.count("Capability Policy", {"is_active": 0})

    # Policies by target type
    by_type = frappe.db.sql("""
        SELECT target_type, COUNT(*) as count, SUM(is_active) as active_count
        FROM `tabCapability Policy`
        GROUP BY target_type
    """, as_dict=True)

    return {
        "active_policies": active,
        "inactive_policies": inactive,
        "by_target_type": by_type,
    }
