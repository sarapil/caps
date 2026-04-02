"""
CAPS Admin API — Bulk Operations & Power Tools
================================================

Admin-only endpoints for bulk capability management, cloning,
usage reports, and the resolution trace debugger.

All endpoints require System Manager or CAPS Admin role.
"""

import frappe
from frappe.utils import now_datetime


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  BULK OPERATIONS                                                     ║
# ╚═══════════════════════════════════════════════════════════════════════╝


@frappe.whitelist()
def bulk_grant(users: str | list, capabilities: str | list) -> dict:
    """
    Grant one or more capabilities to one or more users in a single call.

    Args:
        users: list of user emails (or JSON string)
        capabilities: list of capability names (or JSON string)

    Returns:
        {granted: int, skipped: int, errors: [{user, capability, error}]}
    """
    frappe.only_for(["System Manager"])
    frappe.only_for(["System Manager"])
    frappe.only_for(["CAPS Manager", "System Manager"])


    import json
    if isinstance(users, str):
        users = json.loads(users)
    if isinstance(capabilities, str):
        capabilities = json.loads(capabilities)

    from caps.utils.resolver import invalidate_user_cache

    granted = 0
    skipped = 0
    errors = []

    for user in users:
        for cap in capabilities:
            try:
                if not frappe.db.exists("Capability", cap):
                    errors.append({"user": user, "capability": cap, "error": "Capability not found"})
                    continue

                if not frappe.db.exists("User Capability", user):
                    frappe.get_doc({
                        "doctype": "User Capability",
                        "user": user,
                    }).insert(ignore_permissions=True)

                doc = frappe.get_doc("User Capability", user)

                # Check if already has
                already = False
                for row in doc.direct_capabilities:
                    if row.capability == cap:
                        already = True
                        break

                if already:
                    skipped += 1
                    continue

                doc.append("direct_capabilities", {
                    "capability": cap,
                    "granted_by": frappe.session.user,
                    "granted_on": now_datetime(),
                })
                doc.save(ignore_permissions=True)
                invalidate_user_cache(user)
                granted += 1

            except Exception as e:
                errors.append({"user": user, "capability": cap, "error": str(e)})

    frappe.db.commit()

    # Audit
    _audit_bulk("bulk_grant", users, capabilities, granted)

    # Notify affected users about granted capabilities
    try:
        from caps.notifications import notify_capability_change
        for user in users:
            user_granted = [c for c in capabilities
                           if not any(e["user"] == user and e["capability"] == c for e in errors)]
            if user_granted:
                notify_capability_change(user, granted=user_granted, revoked=[], changed_by=frappe.session.user)
    except Exception:
        pass  # Never let notification failure break the flow

    return {"granted": granted, "skipped": skipped, "errors": errors}


@frappe.whitelist()
def bulk_revoke(users: str | list, capabilities: str | list) -> dict:
    """
    Revoke one or more directly-assigned capabilities from one or more users.

    Returns:
        {revoked: int, skipped: int, errors: [{user, capability, error}]}
    """
    frappe.only_for(["CAPS Manager", "System Manager"])


    import json
    if isinstance(users, str):
        users = json.loads(users)
    if isinstance(capabilities, str):
        capabilities = json.loads(capabilities)

    from caps.utils.resolver import invalidate_user_cache

    revoked = 0
    skipped = 0
    errors = []

    for user in users:
        if not frappe.db.exists("User Capability", user):
            skipped += len(capabilities)
            continue

        try:
            doc = frappe.get_doc("User Capability", user)
            changed = False

            for cap in capabilities:
                found = False
                for row in list(doc.direct_capabilities):
                    if row.capability == cap:
                        doc.remove(row)
                        found = True
                        revoked += 1
                        changed = True
                        break

                if not found:
                    skipped += 1

            if changed:
                doc.save(ignore_permissions=True)
                invalidate_user_cache(user)

        except Exception as e:
            errors.append({"user": user, "capability": "*", "error": str(e)})

    frappe.db.commit()
    _audit_bulk("bulk_revoke", users, capabilities, revoked)

    # Notify affected users about revoked capabilities
    try:
        from caps.notifications import notify_capability_change
        for user in users:
            user_revoked = [c for c in capabilities
                           if not any(e["user"] == user and e["capability"] == c for e in errors)]
            if user_revoked:
                notify_capability_change(user, granted=[], revoked=user_revoked, changed_by=frappe.session.user)
    except Exception:
        pass

    return {"revoked": revoked, "skipped": skipped, "errors": errors}


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  CLONE                                                               ║
# ╚═══════════════════════════════════════════════════════════════════════╝


@frappe.whitelist()
def clone_user_capabilities(source_user: str, target_user: str, include_bundles: bool = True) -> dict:
    """
    Clone direct capabilities (and optionally bundles) from one user to another.

    Does NOT clone group memberships or role-based capabilities (those are
    structural, not user-level).

    Returns:
        {capabilities_cloned: int, bundles_cloned: int, skipped: int}
    """
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    if isinstance(include_bundles, str):
        include_bundles = include_bundles.lower() in ("true", "1", "yes")

    from caps.utils.resolver import invalidate_user_cache

    if not frappe.db.exists("User Capability", source_user):
        frappe.throw(f"Source user '{source_user}' has no capability record")

    source = frappe.get_doc("User Capability", source_user)

    # Ensure target has a User Capability doc
    if not frappe.db.exists("User Capability", target_user):
        frappe.get_doc({
            "doctype": "User Capability",
            "user": target_user,
        }).insert(ignore_permissions=True)

    target = frappe.get_doc("User Capability", target_user)
    existing_caps = {r.capability for r in target.direct_capabilities}
    existing_bundles = {r.bundle for r in target.direct_bundles}

    caps_cloned = 0
    bundles_cloned = 0
    skipped = 0

    for row in source.direct_capabilities:
        if row.capability in existing_caps:
            skipped += 1
            continue
        target.append("direct_capabilities", {
            "capability": row.capability,
            "granted_by": frappe.session.user,
            "granted_on": now_datetime(),
        })
        caps_cloned += 1

    if include_bundles:
        for row in source.direct_bundles:
            if row.bundle in existing_bundles:
                skipped += 1
                continue
            target.append("direct_bundles", {
                "bundle": row.bundle,
                "granted_by": frappe.session.user,
                "granted_on": now_datetime(),
            })
            bundles_cloned += 1

    target.save(ignore_permissions=True)
    invalidate_user_cache(target_user)
    frappe.db.commit()

    # Audit
    _audit_clone(source_user, target_user, caps_cloned, bundles_cloned)

    return {
        "capabilities_cloned": caps_cloned,
        "bundles_cloned": bundles_cloned,
        "skipped": skipped,
    }


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  REPORTS & ANALYTICS                                                 ║
# ╚═══════════════════════════════════════════════════════════════════════╝


@frappe.whitelist()
def capability_usage_report() -> list[dict]:
    """
    Return a usage matrix: for each capability, how many users have it.

    Returns list of:
        {capability, label, is_active, user_count, channels: {direct, group, role}}
    """
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    capabilities = frappe.get_all(
        "Capability",
        filters={"is_active": 1},
        fields=["name", "label", "is_active", "category"],
        order_by="name",
    )

    # Get all users with User Capability docs
    all_user_caps = frappe.get_all("User Capability", pluck="name")

    from caps.utils.resolver import resolve_capabilities

    # Build per-capability counts
    usage: dict[str, dict] = {}
    for cap in capabilities:
        usage[cap["name"]] = {
            "capability": cap["name"],
            "label": cap["label"],
            "category": cap["category"],
            "is_active": cap["is_active"],
            "user_count": 0,
            "users": [],
        }

    for user in all_user_caps:
        try:
            user_caps = resolve_capabilities(user)
            for c in user_caps:
                if c in usage:
                    usage[c]["user_count"] += 1
                    if len(usage[c]["users"]) < 10:  # Limit sample
                        usage[c]["users"].append(user)
        except Exception:
            continue

    return sorted(usage.values(), key=lambda x: -x["user_count"])


@frappe.whitelist()
def effective_permissions_matrix(users: str | list | None = None) -> list[dict]:
    """
    Return the effective capability set for each user (or specified users).

    Returns list of:
        {user, total_count, capabilities: [str]}
    """
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    import json
    if isinstance(users, str):
        users = json.loads(users)

    if not users:
        users = frappe.get_all("User Capability", pluck="name")

    from caps.utils.resolver import resolve_capabilities

    result = []
    for user in users:
        try:
            caps = resolve_capabilities(user)
            result.append({
                "user": user,
                "total_count": len(caps),
                "capabilities": sorted(caps),
            })
        except Exception:
            result.append({"user": user, "total_count": 0, "capabilities": []})

    return sorted(result, key=lambda x: -x["total_count"])


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  RESOLUTION TRACE (Debug)                                           ║
# ╚═══════════════════════════════════════════════════════════════════════╝


@frappe.whitelist()
def trace_capability(user: str, capability: str) -> dict:
    """
    Debug tool: trace exactly how a user gets (or doesn't get) a capability.

    Returns a detailed trace showing which channel(s) provide the capability
    and why it may be missing.
    """
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    from caps.utils.resolver import (
        _all_active_capability_names,
        _collect_direct_user,
        _collect_from_groups,
        _collect_from_roles,
        _enforce_prerequisites,
        _admin_bypass_enabled,
        _guest_empty_set_enabled,
        _is_caps_enabled,
        resolve_capabilities,
    )
    from frappe.utils import now_datetime as _now

    trace = {
        "user": user,
        "capability": capability,
        "found": False,
        "channels": {},
        "settings": {},
        "prerequisites": {},
        "final_resolved": False,
    }

    # Settings context
    trace["settings"] = {
        "caps_enabled": _is_caps_enabled(),
        "admin_bypass": _admin_bypass_enabled(),
        "guest_empty_set": _guest_empty_set_enabled(),
    }

    # Short-circuit checks
    if not _is_caps_enabled():
        trace["found"] = True
        trace["reason"] = "CAPS is globally disabled — all capabilities granted"
        trace["final_resolved"] = True
        return trace

    if user == "Administrator" and _admin_bypass_enabled():
        trace["found"] = True
        trace["reason"] = "Administrator with bypass enabled — all capabilities granted"
        trace["final_resolved"] = True
        return trace

    if user == "Guest" and _guest_empty_set_enabled():
        trace["found"] = False
        trace["reason"] = "Guest with empty-set enabled — no capabilities granted"
        trace["final_resolved"] = False
        return trace

    now = _now()
    active_caps = _all_active_capability_names()

    # Check each channel
    direct = _collect_direct_user(user, now, active_caps)
    groups = _collect_from_groups(user, active_caps)
    roles = _collect_from_roles(user, active_caps)

    trace["channels"] = {
        "direct": {
            "provides": capability in direct,
            "total_caps": len(direct),
        },
        "groups": {
            "provides": capability in groups,
            "total_caps": len(groups),
        },
        "roles": {
            "provides": capability in roles,
            "total_caps": len(roles),
        },
    }

    # If found in any channel, add details
    if capability in direct:
        trace["channels"]["direct"]["detail"] = _trace_direct(user, capability)
    if capability in groups:
        trace["channels"]["groups"]["detail"] = _trace_groups(user, capability)
    if capability in roles:
        trace["channels"]["roles"]["detail"] = _trace_roles(user, capability)

    all_before_prereqs = direct | groups | roles
    trace["found"] = capability in all_before_prereqs

    # Check prerequisites
    prereqs = frappe.get_all(
        "Capability Prerequisite",
        filters={"parent": capability, "parenttype": "Capability", "is_hard": 1},
        pluck="prerequisite",
    )
    if prereqs:
        all_after_prereqs = _enforce_prerequisites(all_before_prereqs)
        trace["prerequisites"] = {
            "has_hard_prereqs": True,
            "required": prereqs,
            "met": [p for p in prereqs if p in all_before_prereqs],
            "missing": [p for p in prereqs if p not in all_before_prereqs],
            "capability_survives": capability in all_after_prereqs,
        }
        trace["final_resolved"] = capability in all_after_prereqs
    else:
        trace["prerequisites"] = {"has_hard_prereqs": False}
        trace["final_resolved"] = trace["found"]

    if not trace["found"]:
        trace["reason"] = _build_missing_reason(user, capability, active_caps)

    # Verify against actual resolver
    actual = resolve_capabilities(user)
    trace["resolver_confirms"] = capability in actual

    return trace


@frappe.whitelist()
def explain_user(user: str) -> dict:
    """
    Debug tool: full resolution breakdown for a user showing all 3 channels.

    Returns:
        {user, total, channels: {direct: [caps], groups: {group: [caps]}, roles: {role: [caps]}},
         prereq_removed: [caps]}
    """
    frappe.only_for(["CAPS User", "CAPS Manager", "System Manager"])


    from caps.utils.resolver import (
        _all_active_capability_names,
        _collect_direct_user,
        _collect_from_groups,
        _collect_from_roles,
        _enforce_prerequisites,
        resolve_capabilities,
    )
    from frappe.utils import now_datetime as _now

    now = _now()
    active_caps = _all_active_capability_names()

    direct = _collect_direct_user(user, now, active_caps)
    groups = _collect_from_groups(user, active_caps)
    roles = _collect_from_roles(user, active_caps)

    pre_prereq = direct | groups | roles
    post_prereq = _enforce_prerequisites(set(pre_prereq))
    removed = pre_prereq - post_prereq

    # Group breakdown
    group_detail = {}
    group_names = frappe.get_all(
        "Permission Group Member",
        filters={"user": user},
        pluck="parent",
    )
    for gn in group_names:
        group_detail[gn] = sorted(
            c for c in groups
            if _cap_from_group(gn, c, active_caps)
        )

    # Role breakdown
    role_detail = {}
    user_roles = frappe.get_roles(user)
    role_maps = frappe.get_all(
        "Role Capability Map",
        filters={"role": ("in", user_roles)},
        fields=["name", "role"],
    )
    for rm in role_maps:
        role_caps_from_map = _caps_from_role_map(rm["name"], active_caps)
        if role_caps_from_map:
            role_detail[rm["role"]] = sorted(role_caps_from_map)

    actual = resolve_capabilities(user)

    return {
        "user": user,
        "total": len(actual),
        "channels": {
            "direct": sorted(direct),
            "groups": group_detail,
            "roles": role_detail,
        },
        "prereq_removed": sorted(removed),
        "final": sorted(actual),
    }


# ─── Trace Helpers ────────────────────────────────────────────────────


def _trace_direct(user: str, capability: str) -> dict:
    """Detail how a direct grant provides a capability."""
    if not frappe.db.exists("User Capability", user):
        return {"via": "none"}

    doc = frappe.get_doc("User Capability", user)

    # Direct capability
    for row in doc.direct_capabilities:
        if row.capability == capability:
            return {
                "via": "direct_capability",
                "granted_by": row.granted_by or "",
                "granted_on": str(row.granted_on or ""),
                "expires_on": str(row.expires_on or ""),
            }

    # Via bundle
    for row in doc.direct_bundles:
        bundle_caps = frappe.get_all(
            "Capability Bundle Item",
            filters={"parent": row.bundle},
            pluck="capability",
        )
        if capability in bundle_caps:
            return {
                "via": "direct_bundle",
                "bundle": row.bundle,
                "granted_by": row.granted_by or "",
                "granted_on": str(row.granted_on or ""),
            }

    return {"via": "unknown"}


def _trace_groups(user: str, capability: str) -> list[dict]:
    """Detail which groups provide a capability."""
    results = []
    group_names = frappe.get_all(
        "Permission Group Member",
        filters={"user": user},
        pluck="parent",
    )
    for gn in group_names:
        # Direct cap from group
        gcaps = frappe.get_all(
            "Permission Group Capability",
            filters={"parent": gn},
            pluck="capability",
        )
        if capability in gcaps:
            results.append({"group": gn, "via": "group_capability"})
            continue

        # Via group bundle
        gbundles = frappe.get_all(
            "Permission Group Bundle",
            filters={"parent": gn},
            pluck="bundle",
        )
        for bn in gbundles:
            bcaps = frappe.get_all(
                "Capability Bundle Item",
                filters={"parent": bn},
                pluck="capability",
            )
            if capability in bcaps:
                results.append({"group": gn, "via": "group_bundle", "bundle": bn})
                break

    return results


def _trace_roles(user: str, capability: str) -> list[dict]:
    """Detail which role maps provide a capability."""
    results = []
    user_roles = frappe.get_roles(user)
    role_maps = frappe.get_all(
        "Role Capability Map",
        filters={"role": ("in", user_roles)},
        fields=["name", "role"],
    )

    for rm in role_maps:
        # Direct cap from role map
        rcaps = frappe.get_all(
            "Role Capability Item",
            filters={"parent": rm["name"]},
            pluck="capability",
        )
        if capability in rcaps:
            results.append({"role": rm["role"], "via": "role_capability"})
            continue

        # Via role bundle
        rbundles = frappe.get_all(
            "Role Capability Bundle",
            filters={"parent": rm["name"]},
            pluck="bundle",
        )
        for bn in rbundles:
            bcaps = frappe.get_all(
                "Capability Bundle Item",
                filters={"parent": bn},
                pluck="capability",
            )
            if capability in bcaps:
                results.append({"role": rm["role"], "via": "role_bundle", "bundle": bn})
                break

    return results


def _build_missing_reason(user: str, capability: str, active_caps: set) -> str:
    """Build a human-readable reason why a capability is missing."""
    if capability not in active_caps:
        return f"Capability '{capability}' is inactive or does not exist"

    if not frappe.db.exists("User Capability", user):
        reasons = ["No User Capability doc"]
    else:
        reasons = ["Not in direct_capabilities or direct_bundles"]

    group_names = frappe.get_all(
        "Permission Group Member",
        filters={"user": user},
        pluck="parent",
    )
    if not group_names:
        reasons.append("User is not in any Permission Groups")
    else:
        reasons.append(f"In {len(group_names)} group(s) but none provide this capability")

    user_roles = frappe.get_roles(user)
    role_maps = frappe.get_all(
        "Role Capability Map",
        filters={"role": ("in", user_roles)},
        pluck="name",
    )
    if not role_maps:
        reasons.append("No Role Capability Maps match user's roles")
    else:
        reasons.append(f"{len(role_maps)} role map(s) found but none provide this capability")

    return " | ".join(reasons)


def _cap_from_group(group_name: str, capability: str, active_caps: set) -> bool:
    """Check if a specific group provides a capability."""
    # Direct
    gcaps = frappe.get_all(
        "Permission Group Capability",
        filters={"parent": group_name},
        pluck="capability",
    )
    if capability in gcaps:
        return True

    # Via bundle
    gbundles = frappe.get_all(
        "Permission Group Bundle",
        filters={"parent": group_name},
        pluck="bundle",
    )
    for bn in gbundles:
        bcaps = frappe.get_all(
            "Capability Bundle Item",
            filters={"parent": bn},
            pluck="capability",
        )
        if capability in bcaps and capability in active_caps:
            return True

    return False


def _caps_from_role_map(role_map_name: str, active_caps: set) -> set:
    """Get all capabilities provided by a role map."""
    caps = set()
    rcaps = frappe.get_all(
        "Role Capability Item",
        filters={"parent": role_map_name},
        pluck="capability",
    )
    for c in rcaps:
        if c in active_caps:
            caps.add(c)

    rbundles = frappe.get_all(
        "Role Capability Bundle",
        filters={"parent": role_map_name},
        pluck="bundle",
    )
    for bn in rbundles:
        bcaps = frappe.get_all(
            "Capability Bundle Item",
            filters={"parent": bn},
            pluck="capability",
        )
        for c in bcaps:
            if c in active_caps:
                caps.add(c)

    return caps


# ─── Audit Helpers ────────────────────────────────────────────────────


def _audit_bulk(action: str, users: list, capabilities: list, count: int):
    """Log bulk operation to audit trail."""
    try:
        frappe.get_doc({
            "doctype": "CAPS Audit Log",
            "user": frappe.session.user,
            "action": action,
            "capability": f"[{len(capabilities)} capabilities]",
            "target_user": f"[{len(users)} users]",
            "result": "allowed",
            "context": frappe.as_json({"count": count, "users": users[:5], "caps": capabilities[:5]}),
            "timestamp": now_datetime(),
            "ip_address": getattr(frappe.local, "request_ip", ""),
        }).insert(ignore_permissions=True)
    except Exception:
        pass


def _audit_clone(source: str, target: str, caps: int, bundles: int):
    """Log clone operation to audit trail."""
    try:
        frappe.get_doc({
            "doctype": "CAPS Audit Log",
            "user": frappe.session.user,
            "action": "clone_capabilities",
            "capability": f"cloned {caps} caps + {bundles} bundles",
            "target_user": target,
            "result": "allowed",
            "context": frappe.as_json({"source": source, "target": target}),
            "timestamp": now_datetime(),
            "ip_address": getattr(frappe.local, "request_ip", ""),
        }).insert(ignore_permissions=True)
    except Exception:
        pass
