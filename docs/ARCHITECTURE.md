# CAPS Architecture

## System Overview

CAPS (Capability-Based Access Control System) is a Frappe application that provides fine-grained access control through atomic capability tokens. It operates as a **complementary layer** on top of Frappe's native role/DocType permission system.

```
┌──────────────────────────────────────────────────────────────────┐
│                        CLIENT BROWSER                             │
│                                                                   │
│  frappe.boot.caps ──→ frappe.caps.enforce(frm) ──→ UI updates   │
│  (loaded on boot)     (every form refresh)        (hide/mask)    │
└─────────────────────────────┬────────────────────────────────────┘
                              │ REST API
┌─────────────────────────────┴────────────────────────────────────┐
│                        FRAPPE SERVER                              │
│                                                                   │
│  ┌──────────────┐  ┌───────────────────┐  ┌──────────────────┐  │
│  │  boot.py     │  │ hooks_integration │  │   9 API modules  │  │
│  │  Injects     │  │ Wildcard hooks:   │  │   54+ endpoints  │  │
│  │  caps into   │  │ on_load → filter  │  │                  │  │
│  │  bootinfo    │  │ before_save →     │  │  api.py          │  │
│  │              │  │   validate        │  │  api_admin.py    │  │
│  └──────┬───────┘  └────────┬──────────┘  │  api_delegation  │  │
│         │                   │             │  api_policies    │  │
│         ▼                   ▼             │  api_requests    │  │
│  ┌─────────────────────────────────────┐  │  api_snapshots   │  │
│  │          RESOLVER ENGINE            │  │  api_impersonate │  │
│  │     utils/resolver.py (697 LOC)     │  │  api_transfer    │  │
│  │                                     │  │  api_dashboard   │  │
│  │  resolve_capabilities(user)         │  └──────────────────┘  │
│  │    ├─ Channel 1: Direct User Caps   │                        │
│  │    ├─ Channel 2: Permission Groups  │                        │
│  │    ├─ Channel 3: Role Mapping       │                        │
│  │    ├─ Channel 4: Hierarchy Expand   │                        │
│  │    └─ Prerequisite Enforcement      │                        │
│  └──────────────┬──────────────────────┘                        │
│                 │                                                │
│  ┌──────────────┴──────────────────────┐                        │
│  │          REDIS CACHE LAYER          │                        │
│  │  caps:user:{email}     (user caps)  │                        │
│  │  caps:fieldmap:{dt}    (field maps) │                        │
│  │  caps:actionmap:{dt}   (action map) │                        │
│  │  caps:prereq_map       (prereqs)    │                        │
│  │  caps:hierarchy_map    (parent→kid) │                        │
│  │  caps:map_version      (counter)    │                        │
│  │  caps:impersonate:{u}  (view-as)    │                        │
│  └─────────────────────────────────────┘                        │
│                                                                   │
│  ┌─────────────────────────────────────┐                        │
│  │     SMART CACHE INVALIDATION        │                        │
│  │  cache_invalidation.py              │                        │
│  │  Wired via doc_events in hooks.py   │                        │
│  │  Each DocType change invalidates    │                        │
│  │  only affected caches               │                        │
│  └─────────────────────────────────────┘                        │
└──────────────────────────────────────────────────────────────────┘
```

---

## Resolution Algorithm

### `resolve_capabilities(user: str) → set[str]`

```
Input: user email
Output: set of capability name strings

Step 0: Special cases
  ├── CAPS disabled? → return ALL active capabilities
  ├── Guest + guest_empty_set? → return empty set
  ├── Administrator + admin_bypass? → return ALL active capabilities
  └── Impersonation active? → recurse with target_user

Step 1: Check Redis cache
  └── Hit? → return cached set

Step 2: Get active capabilities from DB
  └── SELECT name FROM Capability WHERE is_active=1

Step 3: Channel 1 — Direct User Capabilities
  ├── User Capability → direct_capabilities → [capability names]
  └── User Capability → direct_bundles → expand each bundle → [capability names]

Step 4: Channel 2 — Permission Groups
  ├── Find all groups where user is a member
  ├── Group → group_capabilities → [capability names]
  └── Group → group_bundles → expand each bundle → [capability names]

Step 5: Channel 3 — Role-Based
  ├── Get user's Frappe roles
  ├── Find Role Capability Maps for those roles
  ├── Map → role_capabilities → [capability names]
  └── Map → role_bundles → expand each bundle → [capability names]

Step 6: Union all channels
  └── caps = ch1 ∪ ch2 ∪ ch3

Step 7: Channel 4 — Hierarchy Expansion
  ├── Build parent→children map from DB (cached)
  ├── For each cap in user's set, add its active children
  └── Repeat iteratively until no new children found (handles multi-level)

Step 8: Prerequisite Enforcement
  ├── Build prerequisite map from DB (cached)
  ├── For each cap with hard prerequisites:
  │   └── If any prereq missing → remove cap
  └── Repeat until stable (handles transitive deps)

Step 9: Filter to active capabilities only
  └── caps = caps ∩ active_caps

Step 10: Cache in Redis
  └── SET caps:user:{email} → TTL from settings (default 300s)

Return: set of capability names
```

### Field Restriction Resolution

```
get_field_restrictions(doctype, user) → dict

1. Get field maps: SELECT * FROM Field Capability Map WHERE doctype_name=X
   (cached in caps:fieldmap:{doctype})

2. Get user capabilities: resolve_capabilities(user)

3. For each field map:
   if map.capability NOT IN user_caps:
     restrictions[fieldname] = {behavior, mask_pattern, custom_handler, priority}

4. If multiple maps for same field: highest priority wins

Return: {fieldname: {behavior, mask_pattern, ...}}
```

### Action Restriction Resolution

```
get_action_restrictions(doctype, user) → dict

Same pattern as field restrictions, using Action Capability Map.
```

---

## Caching Strategy

### Cache Keys

| Key Pattern | Content | TTL | Invalidated By |
|-------------|---------|-----|----------------|
| `caps:user:{email}` | Resolved capability set | `cache_ttl` (default 300s) | User Capability, Group, Bundle, Role Map changes |
| `caps:fieldmap:{doctype}` | Field restrictions for DocType | `field_map_cache_ttl` (default 600s) | Field Capability Map changes |
| `caps:actionmap:{doctype}` | Action restrictions for DocType | `field_map_cache_ttl` (default 600s) | Action Capability Map changes |
| `caps:prereq_map` | Prerequisite graph | `field_map_cache_ttl` | Capability changes |
| `caps:hierarchy_map` | Parent→children map | `field_map_cache_ttl` | Capability changes |
| `caps:map_version` | Monotonic counter | Never expires | Field/Action Map changes |
| `caps:impersonate:{user}` | Impersonation state JSON | 1800s (30 min) | start/stop impersonation |

### Smart Invalidation

Each DocType has targeted cache invalidation wired via `doc_events` in `hooks.py`:

| DocType Change | What Gets Invalidated |
|----------------|----------------------|
| **Capability** saved/deleted | `prereq_map` + `hierarchy_map` + ALL user caches |
| **User Capability** changed | That specific user's cache |
| **Permission Group** changed | All group members' caches |
| **Capability Bundle** changed | All users referencing that bundle (direct + groups + roles) |
| **Role Capability Map** changed | All users with that Frappe role |
| **Field Capability Map** changed | `map_version` bumped + field map cache cleared |
| **Action Capability Map** changed | `map_version` bumped + action map cache cleared |
| **Capability Policy** changed | `map_version` bumped |

---

## Client-Side Architecture

### Boot Integration

On every page load, `boot.py` injects:

```javascript
frappe.boot.caps = {
    capabilities: ["cap1", "cap2", ...],  // Full resolved set
    field_restrictions: {                  // All DocTypes with restrictions
        "Lead": { "phone": {behavior: "mask", mask_pattern: "{last4}"} }
    },
    action_restrictions: { ... },
    map_version: 42,                       // For client cache invalidation
    impersonating: "user@example.com"      // If impersonation active
}
```

### Client Controller (`frappe.caps`)

The `caps_controller.js` file creates a global `frappe.caps` object that:

1. **Auto-hooks** into every form refresh via `frappe.ui.form.on("*", { refresh: ... })`
2. **Caches** capabilities client-side with 60s TTL
3. **Compares** `map_version` to detect server-side changes
4. **Enforces** field restrictions (hide/mask/read_only) and action restrictions (hide/disable buttons)
5. **Shows impersonation banner** when active

---

## File Structure

```
caps/
├── caps/                         # Frappe app module
│   ├── __init__.py
│   ├── hooks.py                  # App configuration
│   ├── boot.py                   # Session boot injection
│   ├── install.py                # Post-install setup
│   ├── settings_helper.py        # CAPS Settings accessor
│   ├── policy_engine.py          # Temporal policy engine
│   ├── tasks.py                  # Scheduled tasks
│   ├── overrides.py              # Server-side enforcement
│   ├── hooks_integration.py      # Auto doc-event hooks
│   ├── api.py                    # Public API (13 endpoints)
│   ├── api_admin.py              # Admin API (7 endpoints)
│   ├── api_delegation.py         # Delegation API (5 endpoints)
│   ├── api_policies.py           # Policy API (6 endpoints)
│   ├── api_requests.py           # Request API (7 endpoints)
│   ├── api_snapshots.py          # Snapshot API (6 endpoints)
│   ├── api_impersonation.py      # Impersonation API (3 endpoints)
│   ├── api_transfer.py           # Import/Export API (3 endpoints)
│   ├── api_dashboard.py          # Dashboard API (7 endpoints)
│   ├── utils/
│   │   ├── resolver.py           # Resolution engine (697 LOC)
│   │   └── cache_invalidation.py # Smart cache invalidation
│   ├── caps/                     # DocTypes directory
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
│   │       └── (10 child table DocTypes)
│   ├── page/
│   │   └── caps_admin/           # Admin dashboard page
│   ├── public/
│   │   └── js/
│   │       └── caps_controller.js  # Client-side library
│   └── tests/
│       └── (20 test files, 286 tests)
├── README.md
├── ROADMAP.md
└── docs/
    ├── ARCHITECTURE.md           # This file
    ├── API_REFERENCE.md
    ├── DEVELOPER_GUIDE.md
    ├── ADMIN_GUIDE.md
    ├── USER_GUIDE.md
    ├── INTEGRATION_PROMPT.md
    ├── SALES_PITCH.md
    └── AI_CONTEXT.md
```

---

## Security Model

### Defense in Depth

1. **Server-side enforcement** — `auto_filter_fields` strips restricted fields before they reach the browser
2. **Write validation** — `auto_validate_writes` blocks field modifications on save
3. **Client-side UI** — Fields hidden/masked in the form for better UX
4. **Audit trail** — Every check logged for compliance

### Trust Boundaries

- **Never trust the client** — All enforcement is duplicated server-side
- **Administrator bypass** — Configurable (`admin_bypass` in settings)
- **Guest handling** — Configurable (`guest_empty_set` in settings)
- **Impersonation** — Redis-only state, 30-min auto-expiry, full audit trail

### Cache Security

- User cache keys use the exact email: `caps:user:user@example.com`
- No cross-user cache leakage possible
- Impersonation state is per-session user, not target user
- All cache TTLs are configurable with sane defaults
