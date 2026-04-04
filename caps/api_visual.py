# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

"""
CAPS — Visual Graph API Endpoints
====================================
Provides graph data for frappe_visual GraphEngine rendering.
7 endpoints, 12 CAPS-specific node types.
"""
import frappe
from frappe import _


# ═══════════════════════════════════════════════════════════════
# Node Type Registry
# ═══════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_caps_node_types():
    """Return CAPS-specific node type definitions for ColorSystem."""
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])

    return {
        "capability": {
            "bg": "#10B981", "border": "#059669", "text": "#ffffff",
            "icon": "🔑", "shape": "round-rectangle",
        },
        "capability_inactive": {
            "bg": "#94a3b8", "border": "#64748b", "text": "#ffffff",
            "icon": "🔒", "shape": "round-rectangle",
        },
        "bundle": {
            "bg": "#8b5cf6", "border": "#7c3aed", "text": "#ffffff",
            "icon": "📦", "shape": "round-hexagon",
        },
        "group": {
            "bg": "#3b82f6", "border": "#2563eb", "text": "#ffffff",
            "icon": "👥", "shape": "ellipse",
        },
        "role": {
            "bg": "#f59e0b", "border": "#d97706", "text": "#ffffff",
            "icon": "🛡️", "shape": "diamond",
        },
        "user": {
            "bg": "#6366f1", "border": "#4f46e5", "text": "#ffffff",
            "icon": "👤", "shape": "ellipse",
        },
        "policy": {
            "bg": "#ec4899", "border": "#db2777", "text": "#ffffff",
            "icon": "📜", "shape": "round-rectangle",
        },
        "field_map": {
            "bg": "#14b8a6", "border": "#0d9488", "text": "#ffffff",
            "icon": "📝", "shape": "rectangle",
        },
        "action_map": {
            "bg": "#f97316", "border": "#ea580c", "text": "#ffffff",
            "icon": "⚡", "shape": "rectangle",
        },
        "category_hub": {
            "bg": "#059669", "border": "#047857", "text": "#ffffff",
            "icon": "🏷️", "shape": "round-octagon",
        },
        "request": {
            "bg": "#eab308", "border": "#ca8a04", "text": "#ffffff",
            "icon": "✋", "shape": "round-rectangle",
        },
        "rate_limit": {
            "bg": "#ef4444", "border": "#dc2626", "text": "#ffffff",
            "icon": "⏱️", "shape": "round-rectangle",
        },
    }


# ═══════════════════════════════════════════════════════════════
# 1. Capability Hierarchy Graph
# ═══════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_capability_hierarchy():
    """
    Returns full capability hierarchy as nodes+edges for GraphEngine.
    Grouped by category, parent→child edges.
    """
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])

    caps = frappe.get_all(
        "Capability",
        fields=["name", "name1", "capability_label", "category",
                "parent_capability", "is_active", "scope_doctype",
                "app_name", "is_delegatable"],
        limit_page_length=0,
    )

    # Category hub nodes
    categories = set(c.get("category") or "Custom" for c in caps)
    nodes = []
    edges = []

    for cat in sorted(categories):
        nodes.append({
            "id": f"cat:{cat}",
            "label": _(cat),
            "type": "category_hub",
            "icon": "🏷️",
            "summary": {"Category": cat},
            "parent": None,
        })

    for c in caps:
        cap_id = c["name"]
        cat = c.get("category") or "Custom"
        nodes.append({
            "id": cap_id,
            "label": c.get("capability_label") or c.get("name1") or cap_id,
            "type": "capability" if c.get("is_active") else "capability_inactive",
            "icon": "🔑" if c.get("is_active") else "🔒",
            "parent": f"cat:{cat}",
            "summary": {
                _("Category"): cat,
                _("DocType"): c.get("scope_doctype") or "—",
                _("App"): c.get("app_name") or "—",
                _("Active"): _("Yes") if c.get("is_active") else _("No"),
                _("Delegatable"): _("Yes") if c.get("is_delegatable") else _("No"),
            },
        })
        # Parent→child
        if c.get("parent_capability"):
            edges.append({
                "source": c["parent_capability"],
                "target": cap_id,
                "label": _("inherits"),
                "type": "hierarchy",
            })
        else:
            edges.append({
                "source": f"cat:{cat}",
                "target": cap_id,
                "type": "category",
            })

    return {"nodes": nodes, "edges": edges}


# ═══════════════════════════════════════════════════════════════
# 2. Prerequisite Dependency Graph
# ═══════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_prerequisite_graph():
    """
    Returns prerequisite dependency graph.
    Capability → prerequisite edges with hard/soft types.
    """
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])

    caps = frappe.get_all(
        "Capability",
        fields=["name", "capability_label", "name1", "is_active", "category"],
        limit_page_length=0,
    )
    prereqs = frappe.get_all(
        "Capability Prerequisite",
        fields=["parent", "prerequisite", "is_hard"],
        limit_page_length=0,
    )

    cap_map = {c["name"]: c for c in caps}
    nodes = []
    edges = []
    seen_nodes = set()

    for p in prereqs:
        for nid in [p["parent"], p["prerequisite"]]:
            if nid not in seen_nodes:
                seen_nodes.add(nid)
                c = cap_map.get(nid, {})
                nodes.append({
                    "id": nid,
                    "label": c.get("capability_label") or c.get("name1") or nid,
                    "type": "capability" if c.get("is_active", True) else "capability_inactive",
                    "icon": "🔑",
                    "summary": {
                        _("Category"): c.get("category") or "—",
                        _("Active"): _("Yes") if c.get("is_active") else _("No"),
                    },
                })
        edges.append({
            "source": p["prerequisite"],
            "target": p["parent"],
            "label": _("hard prerequisite") if p.get("is_hard") else _("soft prerequisite"),
            "type": "hard_prereq" if p.get("is_hard") else "soft_prereq",
            "color": "#ef4444" if p.get("is_hard") else "#f59e0b",
        })

    return {"nodes": nodes, "edges": edges}


# ═══════════════════════════════════════════════════════════════
# 3. Bundle Composition Graph
# ═══════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_bundle_graph():
    """
    Returns bundle→capability composition graph.
    """
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])

    bundles = frappe.get_all(
        "Capability Bundle",
        fields=["name", "bundle_label", "is_template", "app_name"],
        limit_page_length=0,
    )
    items = frappe.get_all(
        "Capability Bundle Item",
        fields=["parent", "capability", "is_mandatory"],
        limit_page_length=0,
    )
    caps = frappe.get_all(
        "Capability",
        fields=["name", "capability_label", "name1", "category"],
        limit_page_length=0,
    )
    cap_map = {c["name"]: c for c in caps}

    nodes = []
    edges = []
    seen = set()

    for b in bundles:
        nodes.append({
            "id": b["name"],
            "label": b.get("bundle_label") or b["name"],
            "type": "bundle",
            "icon": "📦",
            "summary": {
                _("Template"): _("Yes") if b.get("is_template") else _("No"),
                _("App"): b.get("app_name") or "—",
            },
        })
        seen.add(b["name"])

    for item in items:
        cap_id = item["capability"]
        if cap_id not in seen:
            seen.add(cap_id)
            c = cap_map.get(cap_id, {})
            nodes.append({
                "id": cap_id,
                "label": c.get("capability_label") or c.get("name1") or cap_id,
                "type": "capability",
                "icon": "🔑",
                "summary": {_("Category"): c.get("category") or "—"},
            })
        edges.append({
            "source": item["parent"],
            "target": cap_id,
            "label": _("mandatory") if item.get("is_mandatory") else _("optional"),
            "type": "bundle_contains",
            "color": "#8b5cf6",
        })

    return {"nodes": nodes, "edges": edges}


# ═══════════════════════════════════════════════════════════════
# 4. Group Hierarchy Graph
# ═══════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_group_hierarchy():
    """
    Returns permission group hierarchy as graph.
    """
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])

    groups = frappe.get_all(
        "Permission Group",
        fields=["name", "group_label", "parent_group", "group_type",
                "auto_sync", "managed_by"],
        limit_page_length=0,
    )
    members = frappe.get_all(
        "Permission Group Member",
        fields=["parent", "user"],
        limit_page_length=0,
    )

    member_counts = {}
    for m in members:
        member_counts[m["parent"]] = member_counts.get(m["parent"], 0) + 1

    nodes = []
    edges = []

    for g in groups:
        nodes.append({
            "id": g["name"],
            "label": g.get("group_label") or g["name"],
            "type": "group",
            "icon": "👥",
            "summary": {
                _("Type"): g.get("group_type") or "Manual",
                _("Members"): str(member_counts.get(g["name"], 0)),
                _("Auto Sync"): _("Yes") if g.get("auto_sync") else _("No"),
                _("Manager"): g.get("managed_by") or "—",
            },
        })
        if g.get("parent_group"):
            edges.append({
                "source": g["parent_group"],
                "target": g["name"],
                "type": "group_hierarchy",
                "label": _("subgroup"),
            })

    return {"nodes": nodes, "edges": edges}


# ═══════════════════════════════════════════════════════════════
# 5. Role→Capability Map Graph
# ═══════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_role_capability_graph():
    """
    Returns role→capability mapping graph.
    Shows which Frappe roles map to which CAPS capabilities.
    """
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])

    maps = frappe.get_all(
        "Role Capability Map",
        fields=["name", "role"],
        limit_page_length=0,
    )
    items = frappe.get_all(
        "Role Capability Item",
        fields=["parent", "capability"],
        limit_page_length=0,
    )
    caps = frappe.get_all(
        "Capability",
        fields=["name", "capability_label", "name1", "category"],
        limit_page_length=0,
    )
    cap_map = {c["name"]: c for c in caps}

    nodes = []
    edges = []
    seen = set()

    for m in maps:
        rid = f"role:{m['role']}"
        if rid not in seen:
            seen.add(rid)
            nodes.append({
                "id": rid,
                "label": m["role"],
                "type": "role",
                "icon": "🛡️",
                "summary": {_("Role"): m["role"]},
            })

    for item in items:
        cap_id = item["capability"]
        if cap_id not in seen:
            seen.add(cap_id)
            c = cap_map.get(cap_id, {})
            nodes.append({
                "id": cap_id,
                "label": c.get("capability_label") or c.get("name1") or cap_id,
                "type": "capability",
                "icon": "🔑",
                "summary": {_("Category"): c.get("category") or "—"},
            })
        # Find parent map's role
        parent_map = next((m for m in maps if m["name"] == item["parent"]), None)
        if parent_map:
            edges.append({
                "source": f"role:{parent_map['role']}",
                "target": cap_id,
                "type": "role_grants",
                "color": "#f59e0b",
            })

    return {"nodes": nodes, "edges": edges}


# ═══════════════════════════════════════════════════════════════
# 6. User Capability Comparison (Venn-like)
# ═══════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_user_comparison_graph(user_a: str, user_b: str):
    """
    Returns graph showing common/unique capabilities between two users.
    """
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    from caps.utils.resolver import resolve_capabilities

    caps_a = set(resolve_capabilities(user_a))
    caps_b = set(resolve_capabilities(user_b))

    common = caps_a & caps_b
    only_a = caps_a - caps_b
    only_b = caps_b - caps_a

    all_caps = frappe.get_all(
        "Capability",
        fields=["name", "capability_label", "name1", "category"],
        limit_page_length=0,
    )
    cap_map = {c["name"]: c for c in all_caps}

    nodes = [
        {"id": f"user:{user_a}", "label": user_a, "type": "user", "icon": "👤",
         "summary": {_("Total"): str(len(caps_a)), _("Unique"): str(len(only_a))}},
        {"id": f"user:{user_b}", "label": user_b, "type": "user", "icon": "👤",
         "summary": {_("Total"): str(len(caps_b)), _("Unique"): str(len(only_b))}},
    ]
    edges = []

    def _cap_node(cap_id, zone):
        c = cap_map.get(cap_id, {})
        return {
            "id": cap_id,
            "label": c.get("capability_label") or c.get("name1") or cap_id,
            "type": "capability",
            "icon": "🔑",
            "summary": {
                _("Category"): c.get("category") or "—",
                _("Zone"): zone,
            },
        }

    for cap in only_a:
        nodes.append(_cap_node(cap, _("Only in {0}").format(user_a)))
        edges.append({"source": f"user:{user_a}", "target": cap, "type": "only_a", "color": "#3b82f6"})

    for cap in common:
        nodes.append(_cap_node(cap, _("Common")))
        edges.append({"source": f"user:{user_a}", "target": cap, "type": "common", "color": "#10B981"})
        edges.append({"source": f"user:{user_b}", "target": cap, "type": "common", "color": "#10B981"})

    for cap in only_b:
        nodes.append(_cap_node(cap, _("Only in {0}").format(user_b)))
        edges.append({"source": f"user:{user_b}", "target": cap, "type": "only_b", "color": "#f59e0b"})

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "user_a": user_a,
            "user_b": user_b,
            "total_a": len(caps_a),
            "total_b": len(caps_b),
            "common": len(common),
            "only_a": len(only_a),
            "only_b": len(only_b),
        },
    }


# ═══════════════════════════════════════════════════════════════
# 7. Dashboard Overview Graph (module map)
# ═══════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_dashboard_graph():
    """
    Returns CAPS module overview graph — shows all major components
    and their relationships as a navigable map.
    """
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])

    stats = _get_quick_stats()

    nodes = [
        {"id": "hub", "label": _("CAPS"), "type": "category_hub", "icon": "🛡️",
         "summary": {_("Version"): "1.0.0", _("Capabilities"): str(stats["caps"]),
                     _("Users"): str(stats["users"])}},

        {"id": "mod:capabilities", "label": _("Capabilities"), "type": "capability", "icon": "🔑",
         "summary": {_("Total"): str(stats["caps"]), _("Active"): str(stats["active_caps"])},
         "meta": {"route": "List/Capability"}},

        {"id": "mod:bundles", "label": _("Bundles"), "type": "bundle", "icon": "📦",
         "summary": {_("Total"): str(stats["bundles"])},
         "meta": {"route": "List/Capability Bundle"}},

        {"id": "mod:groups", "label": _("Permission Groups"), "type": "group", "icon": "👥",
         "summary": {_("Total"): str(stats["groups"])},
         "meta": {"route": "List/Permission Group"}},

        {"id": "mod:roles", "label": _("Role Maps"), "type": "role", "icon": "🛡️",
         "summary": {_("Total"): str(stats["role_maps"])},
         "meta": {"route": "List/Role Capability Map"}},

        {"id": "mod:users", "label": _("User Capabilities"), "type": "user", "icon": "👤",
         "summary": {_("Users"): str(stats["users"])},
         "meta": {"route": "List/User Capability"}},

        {"id": "mod:policies", "label": _("Policies"), "type": "policy", "icon": "📜",
         "summary": {_("Active"): str(stats["policies"])},
         "meta": {"route": "List/Capability Policy"}},

        {"id": "mod:field_maps", "label": _("Field Restrictions"), "type": "field_map", "icon": "📝",
         "summary": {_("Rules"): str(stats["field_maps"])},
         "meta": {"route": "List/Field Capability Map"}},

        {"id": "mod:action_maps", "label": _("Action Restrictions"), "type": "action_map", "icon": "⚡",
         "summary": {_("Rules"): str(stats["action_maps"])},
         "meta": {"route": "List/Action Capability Map"}},

        {"id": "mod:requests", "label": _("Requests"), "type": "request", "icon": "✋",
         "summary": {_("Pending"): str(stats["pending_requests"])},
         "meta": {"route": "List/Capability Request"}},

        {"id": "mod:rate_limits", "label": _("Rate Limits"), "type": "rate_limit", "icon": "⏱️",
         "summary": {_("Active"): str(stats["rate_limits"])},
         "meta": {"route": "List/Capability Rate Limit"}},

        {"id": "mod:audit", "label": _("Audit Log"), "type": "category_hub", "icon": "📋",
         "summary": {_("Last 24h"): str(stats["audit_24h"])},
         "meta": {"route": "List/CAPS Audit Log"}},
    ]

    hub = "hub"
    edges = [
        {"source": hub, "target": "mod:capabilities", "type": "module"},
        {"source": hub, "target": "mod:bundles", "type": "module"},
        {"source": hub, "target": "mod:groups", "type": "module"},
        {"source": hub, "target": "mod:roles", "type": "module"},
        {"source": hub, "target": "mod:users", "type": "module"},
        {"source": hub, "target": "mod:policies", "type": "module"},
        {"source": hub, "target": "mod:field_maps", "type": "module"},
        {"source": hub, "target": "mod:action_maps", "type": "module"},
        {"source": hub, "target": "mod:requests", "type": "module"},
        {"source": hub, "target": "mod:rate_limits", "type": "module"},
        {"source": hub, "target": "mod:audit", "type": "module"},
        # Cross-links
        {"source": "mod:capabilities", "target": "mod:bundles", "type": "relates", "label": _("grouped into")},
        {"source": "mod:roles", "target": "mod:capabilities", "type": "relates", "label": _("grants")},
        {"source": "mod:groups", "target": "mod:users", "type": "relates", "label": _("members")},
        {"source": "mod:policies", "target": "mod:capabilities", "type": "relates", "label": _("auto-grants")},
        {"source": "mod:capabilities", "target": "mod:field_maps", "type": "relates", "label": _("restricts")},
        {"source": "mod:capabilities", "target": "mod:action_maps", "type": "relates", "label": _("restricts")},
    ]

    return {"nodes": nodes, "edges": edges}


def _get_quick_stats():
    """Gather quick counts for dashboard."""
    from frappe.utils import now_datetime, add_days
    yesterday = add_days(now_datetime(), -1)

    return {
        "caps": frappe.db.count("Capability"),
        "active_caps": frappe.db.count("Capability", {"is_active": 1}),
        "bundles": frappe.db.count("Capability Bundle"),
        "groups": frappe.db.count("Permission Group"),
        "role_maps": frappe.db.count("Role Capability Map"),
        "users": frappe.db.count("User Capability"),
        "policies": frappe.db.count("Capability Policy", {"is_active": 1}),
        "field_maps": frappe.db.count("Field Capability Map"),
        "action_maps": frappe.db.count("Action Capability Map"),
        "pending_requests": frappe.db.count("Capability Request", {"status": "Pending"}),
        "rate_limits": frappe.db.count("Capability Rate Limit", {"is_active": 1}),
        "audit_24h": frappe.db.count("CAPS Audit Log", {"timestamp": (">", yesterday)}),
    }
