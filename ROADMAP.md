# CAPS Roadmap

> **Last Updated:** June 14, 2026
> **Current Version:** 1.2.0
> **Total Tests:** 366 passing (CAPS) + 95 passing (AuraCRM) = 461 total
> **Status:** ✅ Production Ready (All planned phases complete)

---

## ✅ Completed Phases

### Phase 1: Foundation ✅
- App scaffolding and project structure
- CAPS Settings singleton DocType
- Capability DocType with autoname, validation
- Basic install hook (creates CAPS Admin / CAPS Manager roles)

### Phase 2: Core DocTypes ✅
- Capability Bundle + child table (Capability Bundle Item)
- User Capability + child tables (User Capability Item, User Capability Bundle)
- Role Capability Map + child tables
- Permission Group + child tables (members, capabilities, bundles)
- DocType controllers with validation, autoname, stamps

### Phase 3: Resolution Engine ✅
- `resolve_capabilities()` — 4-channel resolution (direct + groups + roles + hierarchy)
- Bundle expansion logic
- Redis caching per user with configurable TTL
- Active capability filtering
- `check_capability()`, `check_any_capability()`, `require_capability()` helpers
- `get_field_restrictions()`, `get_action_restrictions()` with map caching

### Phase 4: Enforcement Layer ✅
- Field Capability Map DocType (hide / read_only / mask / custom behaviors)
- Action Capability Map DocType (hide / disable / redirect behaviors)
- `filter_response_fields()` — server-side field stripping
- `validate_field_write_permissions()` — server-side write blocking
- `check_action_permission()` — server-side action checks
- `filter_export_fields()` — export masking
- Mask engine: `{lastN}`, `{firstN}`, `***`, `●` default

### Phase 5: Client-Side Controller ✅
- `caps_controller.js` — global `frappe.caps` object
- Auto-hooks into every form refresh
- Field enforcement: hide, read_only, mask, custom
- Action enforcement: button/menu item hide/disable
- Client-side caching with TTL and version comparison
- `frappe.caps.check()`, `checkAny()`, `checkAll()`, `ifCan()`, `enforce()`, `refreshCapabilities()`

### Phase 6: Boot Integration ✅
- `boot.py` — injects capabilities, field/action restrictions, map_version into `frappe.boot.caps`
- Session-level capability availability on every page load

### Phase 7: Smart Cache Invalidation ✅
- `cache_invalidation.py` — targeted invalidation per DocType change
- Capability changes → clear all user caches + prereq_map + hierarchy_map
- User Capability changes → clear that user's cache
- Group changes → clear all members' caches
- Bundle changes → clear all referencing users
- Role Map changes → clear all users with that role
- Field/Action Map changes → bump `map_version` counter

### Phase 8: CAPS Settings & Validation ✅
- `settings_helper.py` — cached settings accessor
- Validation: cache_ttl 10-86400, audit_retention 1-3650
- Kill-switch: `enable_caps` toggles all enforcement
- Admin bypass, guest empty set, debug mode

### Phase 9: Prerequisites ✅
- Capability Prerequisite child table (hard/soft)
- Circular dependency detection (BFS)
- Prerequisite enforcement in resolver (iterative removal until stable)
- `get_dependency_graph()` — prerequisite visualization

### Phase 10: Admin API ✅
- `api_admin.py` — 7 endpoints
- Bulk grant/revoke, clone user capabilities
- Capability usage report, effective matrix
- Trace resolution (full debug), explain capability (per-channel breakdown)

### Phase 11: Public API ✅
- `api.py` — 13 endpoints
- check/batch check, get my capabilities, get restrictions
- Grant/revoke (admin), compare users, bust cache
- Prerequisite graph and satisfaction check

### Phase 12: Capability Policies ✅
- Capability Policy DocType (time-bound, auto-applying)
- `policy_engine.py` — apply_policies, expire_policies, preview
- Scope types: Role, Department, User List
- Grant types: Capability or Bundle
- Policy-tagged grants for targeted revocation

### Phase 13: Self-Service Requests ✅
- Capability Request DocType (Pending → Approved/Rejected/Cancelled)
- `api_requests.py` — 7 endpoints
- Full workflow: submit → approve (auto-grant) → notify
- Priority levels, duplicate prevention, owner cancellation

### Phase 14: Delegation ✅
- `api_delegation.py` — 5 endpoints
- Scoped delegation (delegator must hold cap, cap must be delegatable)
- Delegation enabled/disabled in settings, optional reason
- View delegatable caps, view own delegations, revoke

### Phase 15: Scheduled Tasks ✅
- `tasks.py` — 5 scheduled jobs
- Hourly: cleanup expired capabilities/bundles
- Daily: sync auto-sync groups, cleanup old audit logs
- Daily: apply active policies, expire old policies, check expiry notifications

### Phase 16: Import/Export ✅
- `api_transfer.py` — 3 endpoints
- Export full config as JSON (selective: caps, bundles, maps, policies, groups)
- Import with merge or overwrite mode
- Dry-run validation
- Round-trip fidelity

### Phase 17: Capability Snapshots ✅
- Capability Snapshot DocType
- `api_snapshots.py` — 6 endpoints
- Take point-in-time snapshot, compare two snapshots, compare with current
- Snapshot history, restore to snapshot state
- Source types: manual, scheduled, pre_change, post_change

### Phase 18: Admin Dashboard ✅
- CAPS Admin page (`/app/caps-admin`)
- Stats cards (10 metrics), user lookup, active policies table
- Recent audit log, expiring-soon list
- Quick actions: export, import, bust cache, new capability

### Phase 19: Dashboard Analytics API ✅
- `api_dashboard.py` — 7 endpoints
- Stats summary, capability distribution, audit timeline
- Expiry forecast, request summary, delegation summary, policy summary

### Phase 20: Impersonation ✅
- `api_impersonation.py` — 3 endpoints (start, stop, status)
- Redis-based state with 30-min TTL
- Resolver integration: impersonating user resolves target's caps
- Boot injection: `impersonating` field
- Client: orange fixed banner with Stop button

### Phase 21: Auto Doc-Event Hooks ✅
- `hooks_integration.py` — wildcard doc_events for zero-code enforcement
- `auto_filter_fields()` — on_load: auto-strip restricted fields
- `auto_validate_writes()` — before_save: auto-block unauthorized writes
- `on_login_audit()` — on_session_creation: log login + capability count

### Phase 22: Capability Hierarchy ✅
- `parent_capability` field on Capability DocType
- `_get_hierarchy_map()` — cached parent→children map
- `_expand_hierarchy()` — iterative BFS expansion (multi-level)
- `get_capability_tree()` — nested tree API endpoint
- Cache invalidation for hierarchy_map

### Phase 23: Tests & Validation ✅
- 286 tests across 20 test files — ALL PASSING
- test_impersonation.py (10), test_hierarchy.py (12), test_hooks_integration.py (6)

### Phase 24: Workspace Enhancements ✅
- CAPS workspace with shortcuts for all major DocTypes
- Quick-access shortcuts: Capability Snapshots, Action Maps
- Report shortcuts: Capability Coverage, User Access Matrix, CAPS Audit Report
- Reports link card in workspace navigation

### Phase 25: Notification System ✅
- `notifications.py` — centralized notification engine (10 functions)
- In-app Notification Log for capability grant/revoke changes
- Email notifications for request approve/reject
- Delegation notifications
- Expiry warning notifications
- Weekly admin digest (`weekly_admin_digest` scheduled task)
- `get_notification_config` hook for bell icon badge
- Real-time event publishing
- Settings toggles: `notify_on_capability_change`, `email_on_request`, `enable_admin_digest`
- test_notifications.py (8 tests)

### Phase 26: Group Hierarchy ✅
- `enable_group_hierarchy` setting toggle
- Resolver: `_expand_group_ancestors()` — BFS ancestor traversal
- Resolver: `_get_group_hierarchy_map()` — cached {group: parent} mapping
- Resolver: temp membership filtering via `valid_from`/`valid_till`
- Cache invalidation cascade to descendant group members
- `api_groups.py` — 6 endpoints: tree, ancestors, descendants, effective members, temp member, effective capabilities
- `permission_group_member.json` — `valid_from`/`valid_till` fields for temporary membership
- Hourly task: `expire_temp_group_memberships`
- test_group_hierarchy.py (19 tests)

### Phase 27: Reporting ✅
- 3 Script Reports under `caps/caps/report/`:
- **Capability Coverage** — DocTypes with field/action maps, user counts per capability, coverage status
- **User Access Matrix** — Users × capabilities matrix with D/G/R source indicators
- **CAPS Audit Report** — Filterable audit log with date range, user, action, result filters
- Each report has JS filters for interactive exploration
- test_reports.py (14 tests)

---

## 🔲 Future Phases

### Phase 28: Multi-Tenancy ✅
- [x] CAPS Site Profile DocType — store per-site capability configurations
- [x] `api_tenancy.py` — 6 endpoints: snapshot, compare profiles, compare with current, apply profile, list/detail
- [x] Cross-site capability comparison with structured diff (capabilities, bundles, field/action maps)
- [x] Snapshot current config into profile for centralized management
- [x] test_tenancy.py (11 tests)

### Phase 29: API Rate Limiting ✅
- [x] Capability Rate Limit DocType — per-capability rate rules (hour/day/week/month windows)
- [x] `rate_limiter.py` — Redis-based sliding-window rate limiter engine
- [x] `api_rate_limits.py` — 5 endpoints: check, record, stats, reset (admin), list all (admin)
- [x] Per-user and global scope modes
- [x] Notification on limit reached
- [x] Cache invalidation on rule changes
- [x] test_rate_limiting.py (9 tests)

### Phase 30: UI Enhancements ✅
- [x] CAPS Graph page — force-directed SVG visualization (hierarchy, prerequisites, bundles, groups)
- [x] CAPS Compare page — side-by-side user capability comparison with colored pills
- [x] Search/filter, zoom controls, click-to-navigate to DocType
- [x] No external dependencies (vanilla JS + SVG)

### Phase 31: Integration Hub ✅
- [x] CAPS Integration Pack DocType — custom and built-in pack management
- [x] `api_integrations.py` — 4 endpoints: list packs, preview, install, uninstall
- [x] 4 built-in packs: ERPNext Core (13 caps, 4 bundles), ERPNext Sensitive (4 caps, 3 field maps), HRMS Core (8 caps, 2 bundles), Data Protection (5 caps, 1 bundle, 2 field maps)
- [x] Idempotent install (skips existing), clean uninstall
- [x] test_integrations.py (9 tests)

### Phase 32: Performance Optimization ✅
- [x] `performance.py` — 4 optimization strategies
- [x] Lazy Resolution: `lazy_has_capability()` — short-circuit single-cap checks across 3 channels
- [x] Differential Cache: `apply_cache_delta()` — add/remove from cached set without full recalculation
- [x] Batch Resolution: `batch_resolve()` — resolve multiple users with shared DB queries
- [x] Cache Warming: `warm_caches()` / `warm_map_caches()` — daily pre-population for active users
- [x] test_performance.py (10 tests)

---

## 📋 Known Improvements (Backlog)

- [ ] RTL/Arabic translations for CAPS UI
- [ ] Print format restrictions (beyond action maps)
- [ ] List view column filtering based on capabilities
- [ ] Conditional capability grants (if user has field X = Y, grant cap)
- [ ] Capability tagging/categorization beyond categories
- [ ] Bulk user capability editor UI
- [ ] Capability lifecycle management (draft → active → deprecated → archived)
