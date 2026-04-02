"""
CAPS – Capability Snapshots
============================

Point-in-time snapshots of a user's resolved capabilities.
Useful for auditing, before/after comparisons, and rollback planning.
"""

import json
import frappe
from frappe.utils import now_datetime


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  TAKE SNAPSHOT                                                       ║
# ╚═══════════════════════════════════════════════════════════════════════╝


@frappe.whitelist()
def take_snapshot(
    user: str,
    label: str = "",
    source: str = "manual",
    notes: str = "",
) -> dict:
    """
    Capture the current resolved capabilities for a user.

    Args:
        user: The user email to snapshot
        label: Optional human-readable label
        source: One of manual, scheduled, pre_change, post_change
        notes: Optional notes

    Returns:
        The created Capability Snapshot doc as dict
    """
    frappe.only_for(["System Manager", "CAPS Admin"])

    if not frappe.db.exists("User", user):
        frappe.throw(f"User {user} does not exist")

    from caps.utils.resolver import resolve_capabilities

    resolved = resolve_capabilities(user)

    # Build structured snapshot data
    snapshot_data = {
        "resolved_capabilities": sorted(resolved),
        "capability_count": len(resolved),
        "snapshot_timestamp": str(now_datetime()),
        "sources": _get_capability_sources(user),
    }

    doc = frappe.get_doc({
        "doctype": "Capability Snapshot",
        "user": user,
        "snapshot_label": label or f"Snapshot {str(now_datetime())[:19]}",
        "snapshot_date": now_datetime(),
        "created_by": frappe.session.user,
        "capabilities_json": json.dumps(snapshot_data, indent=2),
        "source": source,
        "notes": notes,
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return doc.as_dict()


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  COMPARE SNAPSHOTS                                                   ║
# ╚═══════════════════════════════════════════════════════════════════════╝


@frappe.whitelist()
def compare_snapshots(snapshot1: str, snapshot2: str) -> dict:
    """
    Compare two snapshots and return the diff.

    Args:
        snapshot1: Name of the first (older) snapshot
        snapshot2: Name of the second (newer) snapshot

    Returns:
        {added: [...], removed: [...], unchanged: [...],
         snapshot1_info: {...}, snapshot2_info: {...}}
    """
    frappe.only_for(["System Manager", "CAPS Admin", "CAPS Manager"])

    doc1 = frappe.get_doc("Capability Snapshot", snapshot1)
    doc2 = frappe.get_doc("Capability Snapshot", snapshot2)

    data1 = json.loads(doc1.capabilities_json)
    data2 = json.loads(doc2.capabilities_json)

    caps1 = set(data1.get("resolved_capabilities", []))
    caps2 = set(data2.get("resolved_capabilities", []))

    added = sorted(caps2 - caps1)
    removed = sorted(caps1 - caps2)
    unchanged = sorted(caps1 & caps2)

    return {
        "added": added,
        "removed": removed,
        "unchanged": unchanged,
        "added_count": len(added),
        "removed_count": len(removed),
        "unchanged_count": len(unchanged),
        "snapshot1_info": {
            "name": doc1.name,
            "user": doc1.user,
            "date": str(doc1.snapshot_date),
            "label": doc1.snapshot_label,
            "count": data1.get("capability_count", 0),
        },
        "snapshot2_info": {
            "name": doc2.name,
            "user": doc2.user,
            "date": str(doc2.snapshot_date),
            "label": doc2.snapshot_label,
            "count": data2.get("capability_count", 0),
        },
    }


@frappe.whitelist()
def compare_with_current(snapshot_name: str) -> dict:
    """
    Compare a snapshot with the user's current resolved capabilities.
    """
    frappe.only_for(["System Manager", "CAPS Admin", "CAPS Manager"])

    doc = frappe.get_doc("Capability Snapshot", snapshot_name)
    data = json.loads(doc.capabilities_json)
    old_caps = set(data.get("resolved_capabilities", []))

    from caps.utils.resolver import resolve_capabilities
    current_caps = set(resolve_capabilities(doc.user))

    added = sorted(current_caps - old_caps)
    removed = sorted(old_caps - current_caps)
    unchanged = sorted(old_caps & current_caps)

    return {
        "added": added,
        "removed": removed,
        "unchanged": unchanged,
        "added_count": len(added),
        "removed_count": len(removed),
        "unchanged_count": len(unchanged),
        "snapshot_info": {
            "name": doc.name,
            "user": doc.user,
            "date": str(doc.snapshot_date),
            "label": doc.snapshot_label,
            "count": data.get("capability_count", 0),
        },
        "current_count": len(current_caps),
    }


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  SNAPSHOT HISTORY                                                    ║
# ╚═══════════════════════════════════════════════════════════════════════╝


@frappe.whitelist()
def get_snapshot_history(
    user: str,
    limit: int = 20,
    source: str = "",
) -> list:
    """
    List snapshots for a user, newest first.
    """
    frappe.only_for(["System Manager", "CAPS Admin", "CAPS Manager"])

    filters = {"user": user}
    if source:
        filters["source"] = source

    snapshots = frappe.get_all(
        "Capability Snapshot",
        filters=filters,
        fields=["name", "user", "snapshot_label", "snapshot_date",
                "source", "created_by", "notes"],
        order_by="snapshot_date desc",
        limit=int(limit),
    )

    # Add capability count from JSON
    for s in snapshots:
        try:
            json_val = frappe.db.get_value("Capability Snapshot",
                                            s["name"], "capabilities_json")
            data = json.loads(json_val) if json_val else {}
            s["capability_count"] = data.get("capability_count", 0)
        except (json.JSONDecodeError, TypeError):
            s["capability_count"] = 0

    return snapshots


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  RESTORE SNAPSHOT                                                    ║
# ╚═══════════════════════════════════════════════════════════════════════╝


@frappe.whitelist()
def restore_snapshot(snapshot_name: str, dry_run: bool = True) -> dict:
    """
    Restore a user's direct capabilities to match a snapshot.

    Only restores *direct* capabilities (not role/group-inherited ones).
    Returns what would change (dry_run=True) or applies changes.

    Args:
        snapshot_name: The snapshot to restore from
        dry_run: If True, only preview changes. If False, apply them.

    Returns:
        {to_grant: [...], to_revoke: [...], applied: bool}
    """
    frappe.only_for(["System Manager", "CAPS Admin"])

    dry_run = _to_bool(dry_run)
    doc = frappe.get_doc("Capability Snapshot", snapshot_name)
    user = doc.user
    data = json.loads(doc.capabilities_json)
    snapshot_caps = set(data.get("resolved_capabilities", []))

    # Get current direct capabilities
    from caps.utils.resolver import resolve_capabilities
    current_caps = set(resolve_capabilities(user))

    to_grant = sorted(snapshot_caps - current_caps)
    to_revoke = sorted(current_caps - snapshot_caps)

    result = {
        "to_grant": to_grant,
        "to_revoke": to_revoke,
        "user": user,
        "snapshot": snapshot_name,
        "applied": False,
    }

    if dry_run:
        return result

    # Apply changes
    uc_name = frappe.db.get_value("User Capability", {"user": user}, "name")
    if not uc_name:
        uc = frappe.get_doc({"doctype": "User Capability", "user": user})
        uc.insert(ignore_permissions=True)
        uc_name = uc.name

    uc_doc = frappe.get_doc("User Capability", uc_name)

    # Revoke: remove items not in snapshot
    current_direct = [row.capability for row in uc_doc.direct_capabilities]
    uc_doc.direct_capabilities = [
        row for row in uc_doc.direct_capabilities
        if row.capability not in to_revoke
    ]

    # Grant: add items from snapshot that are valid capabilities
    for cap in to_grant:
        if frappe.db.exists("Capability", cap):
            uc_doc.append("direct_capabilities", {"capability": cap})

    uc_doc.save(ignore_permissions=True)
    frappe.db.commit()

    # Take a post-restore snapshot
    take_snapshot(user, label=f"Post-restore from {snapshot_name}", source="post_change")

    result["applied"] = True
    return result


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  HELPERS                                                             ║
# ╚═══════════════════════════════════════════════════════════════════════╝


def _get_capability_sources(user: str) -> dict:
    """
    Break down where a user's capabilities come from.
    Returns {direct: [...], bundles: {...}, roles: {...}, groups: {...}}
    """
    sources = {"direct": [], "bundles": {}, "roles": {}, "groups": {}}

    # Direct capabilities
    uc = frappe.db.get_value("User Capability", {"user": user}, "name")
    if uc:
        items = frappe.get_all(
            "User Capability Item",
            filters={"parent": uc},
            pluck="capability",
        )
        sources["direct"] = sorted(items)

        # Direct bundles
        bundles = frappe.get_all(
            "User Capability Bundle",
            filters={"parent": uc},
            pluck="bundle",
        )
        for b in bundles:
            caps = frappe.get_all(
                "Capability Bundle Item",
                filters={"parent": b},
                pluck="capability",
            )
            sources["bundles"][b] = sorted(caps)

    # Role-based capabilities
    user_roles = frappe.get_all(
        "Has Role",
        filters={"parent": user, "parenttype": "User"},
        pluck="role",
    )
    role_maps = frappe.get_all(
        "Role Capability Map",
        filters={"role": ("in", user_roles)} if user_roles else {},
        fields=["name", "role"],
    )
    for rm in role_maps:
        caps = frappe.get_all(
            "Role Capability Item",
            filters={"parent": rm["name"]},
            pluck="capability",
        )
        if caps:
            sources["roles"][rm["role"]] = sorted(caps)

    # Group-based capabilities
    user_groups = frappe.get_all(
        "Permission Group Member",
        filters={"user": user},
        pluck="parent",
    )
    for g in user_groups:
        caps = frappe.get_all(
            "Permission Group Capability",
            filters={"parent": g},
            pluck="capability",
        )
        if caps:
            sources["groups"][g] = sorted(caps)

    return sources


def _to_bool(val):
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes")
    return bool(val)
