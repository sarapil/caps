# CAPS — AI Context Document

> This file provides complete technical context for AI assistants working with the CAPS codebase.

---

## Identity

- **App**: CAPS (Capability-Based Access Control System)
- **Framework**: Frappe v16+ (Python + MariaDB + Redis)
- **Path**: `/workspace/development/frappe-bench/apps/caps/`
- **Module**: `caps` (single module)
- **Version**: 1.0.0
- **License**: Proprietary — Arkan Labs
- **Tests**: 286 passing (20 test files)
- **Python**: ≥3.10

---

## Critical Path Layout

```
caps/                          ← App root
├── caps/                      ← Frappe module (double nesting)
│   ├── caps/                  ← DocTypes (triple nesting)
│   │   └── doctype/
│   │       ├── capability/
│   │       ├── capability_bundle/
│   │       ├── user_capability/
│   │       ├── role_capability_map/
│   │       ├── permission_group/
│   │       ├── field_capability_map/
│   │       ├── action_capability_map/
│   │       ├── capability_policy/
│   │       ├── capability_request/
│   │       ├── capability_snapshot/
│   │       ├── caps_audit_log/
│   │       ├── caps_settings/
│   │       └── (10 child tables)
│   ├── utils/
│   │   ├── resolver.py         ← Core engine (697 LOC)
│   │   └── cache_invalidation.py
│   ├── api.py                  ← Public API (13 endpoints)
│   ├── api_admin.py            ← Admin API (7 endpoints)
│   ├── api_delegation.py       ← Delegation API (5 endpoints)
│   ├── api_policies.py         ← Policy API (6 endpoints)
│   ├── api_requests.py         ← Request API (7 endpoints)
│   ├── api_snapshots.py        ← Snapshot API (6 endpoints)
│   ├── api_impersonation.py    ← Impersonation API (3 endpoints)
│   ├── api_transfer.py         ← Import/Export API (3 endpoints)
│   ├── api_dashboard.py        ← Dashboard API (7 endpoints)
│   ├── overrides.py            ← Server enforcement (mask, filter, validate)
│   ├── hooks_integration.py    ← Wildcard doc_event hooks
│   ├── boot.py                 ← Session boot injection
│   ├── hooks.py                ← App hook configuration
│   ├── install.py              ← Post-install (creates roles)
│   ├── settings_helper.py      ← CAPS Settings accessor
│   ├── policy_engine.py        ← Temporal policy engine
│   ├── tasks.py                ← Scheduled tasks
│   ├── page/caps_admin/        ← Admin dashboard page
│   ├── public/js/caps_controller.js  ← Client-side library
│   └── tests/                  ← 20 test files (286 tests)
├── README.md
├── ROADMAP.md
└── docs/                       ← Documentation
```

---

## DocType Field Names (CRITICAL — Use Exact Names)

### Capability
- `name1` → autoname from this field
- `label`, `category` (Select: Field/Action/Workflow/Report/API/Module/Custom)
- `scope_doctype` (Link → DocType), `scope_field`, `scope_action`
- `parent_capability` (Link → Capability) — hierarchy
- `description`, `is_active` (default 1), `is_delegatable` (default 0)
- `app_name`, `prerequisites` (Table → Capability Prerequisite: `prerequisite` Link, `is_hard` Check)

### Capability Bundle (autoname: prompt)
- `label`, `description`, `is_template`
- `capabilities` (Table → Capability Bundle Item: `capability` Link, `is_mandatory` Check)

### User Capability (autoname: field:user — ONE per user)
- `user` (Link → User, unique)
- `direct_capabilities` (Table → User Capability Item: `capability`, `granted_by`, `granted_on`, `expires_on`, `delegated_by`, `notes`)
- `direct_bundles` (Table → User Capability Bundle: `bundle`, `granted_by`, `granted_on`, `expires_on`)

### Role Capability Map (autoname: field:role — ONE per role)
- `role` (Link → Role, unique)
- `role_capabilities` (Table → Role Capability Item: `capability` Link)
- `role_bundles` (Table → Role Capability Bundle: `bundle` Link)

### Permission Group (autoname: prompt)
- `group_name`, `sync_type` (Manual/Department Sync/Branch Sync/Custom Query)
- `sync_source`, `custom_query`, `sync_frequency`, `is_active`
- `parent_group` (Link → Permission Group), `managed_by` (Link → User)
- `members` (Table → Permission Group Member: `user`, `added_by`, `added_on`)
- `group_capabilities` (Table → Permission Group Capability: `capability`)
- `group_bundles` (Table → Permission Group Bundle: `bundle`)

### Field Capability Map (autoname: hash)
- `doctype_name` (Link → DocType), `fieldname`, `field_label` (auto-fetched, read_only)
- `capability` (Link → Capability), `behavior` (hide/read_only/mask/custom)
- `mask_pattern`, `custom_handler` (Code), `priority` (Int)

### Action Capability Map (autoname: hash)
- `doctype_name` (Link → DocType), `action_id`, `action_type` (button/menu_item/workflow_action/print_format/custom)
- `capability` (Link → Capability), `behavior` (hide/disable/redirect), `redirect_url`

### CAPS Settings (singleton)
- `enable_caps`, `debug_mode`, `caps_version` (read_only Int)
- `cache_ttl` (300), `field_map_cache_ttl` (600)
- `audit_retention_days` (90), `enable_audit_logging` (1)
- `admin_bypass` (1), `guest_empty_set` (1)
- `expiry_warning_days` (7), `enable_expiry_notifications` (1)
- `enable_delegation` (1), `require_delegation_reason` (0)

### CAPS Audit Log (autoname: hash, in_create=1)
- `user`, `action` (16 values), `result` (allowed/denied), `capability`
- `target_user`, `target_group`, `context` (JSON), `timestamp`, `ip_address`

---

## Redis Cache Keys

| Key | Content | TTL |
|-----|---------|-----|
| `caps:user:{email}` | Set of capability names | `cache_ttl` (default 300s) |
| `caps:fieldmap:{doctype}` | Field restrictions dict | `field_map_cache_ttl` (default 600s) |
| `caps:actionmap:{doctype}` | Action restrictions dict | `field_map_cache_ttl` |
| `caps:prereq_map` | {cap: [prereq1, prereq2]} | `field_map_cache_ttl` |
| `caps:hierarchy_map` | {parent: [child1, child2]} | `field_map_cache_ttl` |
| `caps:map_version` | Monotonic integer counter | Never expires |
| `caps:impersonate:{user}` | JSON: target_user, started_at, admin_user | 1800s |

---

## Resolution Algorithm (resolve_capabilities)

```
1. Special cases: disabled → all caps, Guest → empty, Admin → all caps, Impersonation → recurse
2. Check Redis cache → return if hit
3. Channel 1: Direct User Capabilities (direct_capabilities + expand bundles)
4. Channel 2: Permission Groups (members → group_capabilities + expand bundles)
5. Channel 3: Role Mapping (user roles → role_capabilities + expand bundles)
6. Union channels 1-3
7. Channel 4: Hierarchy expansion (parent → children, iterative BFS)
8. Prerequisite enforcement (remove caps with unmet hard prereqs, iterate until stable)
9. Filter to active capabilities only
10. Cache result in Redis
```

---

## Key Patterns

### Gameplan Conflict
Gameplan creates `GP User Profile` docs linked to users, blocking user deletion in tests. Use `_safe_delete_user()`:
```python
def _safe_delete_user(email):
    if not frappe.db.exists("User", email): return
    try:
        frappe.delete_doc("User", email, force=True, ignore_permissions=True)
    except:
        for gp in frappe.get_all("GP User Profile", filters={"user": email}, pluck="name"):
            frappe.delete_doc("GP User Profile", gp, force=True, ignore_permissions=True)
        frappe.delete_doc("User", email, force=True, ignore_permissions=True)
```

### Test Prefixing
All test data uses unique prefixes: `capstest_res_`, `capstest_imp_`, `capstest_hier_`, etc.

### Pyright False Positives
Frappe's dynamic attributes (`frappe.session`, `frappe.cache`, `frappe.get_all`, etc.) trigger Pyright errors. These are NOT real errors.

### Capability Name Validation
Names must have at least 2 parts separated by `:` (e.g., `field:phone` minimum). Category must be valid Select value.

---

## Hooks Configuration

```python
# Wildcard doc_events — auto-enforce on ALL DocTypes
doc_events = {
    "*": {
        "on_load": "caps.hooks_integration.auto_filter_fields",
        "before_save": "caps.hooks_integration.auto_validate_writes",
    },
    # Per-DocType cache invalidation (Capability, User Capability, etc.)
}

# Session
on_session_creation = "caps.hooks_integration.on_login_audit"
boot_session = "caps.boot.boot_session"

# Scheduler
scheduler_events = {
    "cron": {"0 * * * *": ["caps.tasks.cleanup_expired_capabilities"]},
    "daily": [...sync_groups, cleanup_audit, apply_policies, expire_policies, check_expiry...]
}
```

---

## Companion App: AuraCRM

AuraCRM at `/workspace/development/frappe-bench/apps/auracrm/` integrates with CAPS via:
- `auracrm/setup/caps_setup.py` — 80+ capabilities, 5 bundles, role maps, field/action maps
- `auracrm/caps_hooks.py` — Doc event handlers for Lead/Opportunity field filtering
- 54 CAPS integration tests in `test_caps_integration.py`
