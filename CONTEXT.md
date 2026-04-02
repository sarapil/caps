# CAPS — Technical Context

## Overview

**Capability-Based Access Control System for Frappe.** CAPS replaces traditional role-only permission models with fine-grained, capability-based access control. It provides field-level, action-level, and document-level restrictions, along with policy enforcement, rate limiting, delegation, impersonation, permission groups, and audit logging. Every custom app in the workspace declares its capabilities via `caps_capabilities` in hooks.py, and CAPS enforces them at runtime.

- **Publisher:** Arkan Labs
- **Version:** 1.0.0
- **License:** Proprietary
- **Color:** `#10B981` (emerald green)
- **Dependencies:** `frappe`, `frappe_visual`

## Architecture

- **Framework:** Frappe v16
- **Modules:** CAPS (single module)
- **DocTypes:** 24 (including child tables)
- **API Files:** 14
- **Pages:** 5
- **Reports:** 3
- **Scheduled Tasks:** 9 (hourly, daily, weekly)

### Boot & Session Integration

- `boot_session` injects user capabilities into every session
- `on_session_creation` triggers login audit
- `doc_events["*"]` fires `auto_filter_fields` (on_load) and `auto_validate_writes` (before_save) for universal enforcement

## Key Components

### Core Engine

| File | Purpose |
|------|---------|
| `policy_engine.py` | Applies and expires capability policies (daily) |
| `rate_limiter.py` | Enforces per-capability rate limits |
| `cache_invalidation.py` | Invalidates Redis cache on any capability/group/bundle/map change |
| `hooks_integration.py` | Universal doc_events: field filtering + write validation |
| `performance.py` | Performance monitoring and optimization |
| `settings_helper.py` | CAPS Settings accessor utilities |

### API Layer (14 endpoints)

| File | Purpose |
|------|---------|
| `api.py` | Core capability check / resolve / assign APIs |
| `api_admin.py` | Admin management endpoints |
| `api_dashboard.py` | Dashboard data & statistics |
| `api_delegation.py` | Capability delegation between users |
| `api_groups.py` | Permission group management |
| `api_impersonation.py` | User impersonation for debugging |
| `api_integrations.py` | CAPS Integration Pack management |
| `api_policies.py` | Policy CRUD and application |
| `api_rate_limits.py` | Rate limit configuration |
| `api_requests.py` | Capability request/approval workflow |
| `api_snapshots.py` | Point-in-time capability snapshots |
| `api_tenancy.py` | Multi-tenant capability scoping |
| `api_transfer.py` | Bulk capability transfer between users |
| `api_visual.py` | Graph/visual data for frappe_visual components |

### Pages

| Page | Route | Purpose |
|------|-------|---------|
| `caps_admin` | `/desk/caps-admin` | Main admin dashboard |
| `caps_graph` | `/desk/caps-graph` | Interactive capability graph explorer |
| `caps_compare` | `/desk/caps-compare` | Side-by-side user capability comparison |
| `caps_about` | `/caps-about` | App showcase for decision makers |
| `caps_onboarding` | `/caps-onboarding` | Guided onboarding storyboard |

### Frontend

| File | Purpose |
|------|---------|
| `caps_bootstrap.js` | Initialization, namespace setup |
| `caps_controller.js` | Core capability check/enforce logic (client-side) |
| `caps_sidebar.js` | Custom sidebar with CAPS navigation |
| `caps_contextual_help.js` | Contextual help (❓) on forms/reports |
| `caps_brand.css` | Brand colors and visual identity |
| `caps_sidebar.css` | Sidebar styling |

## DocType Summary

| DocType | Purpose |
|---------|---------|
| **Capability** | Atomic permission unit (e.g., "view_dashboard", "approve_orders") |
| **User Capability** | Assignment of a capability to a user (with optional expiry) |
| **Capability Bundle** | Named group of capabilities (e.g., "Finance Viewer") |
| **Capability Bundle Item** | Child: capability reference within a bundle |
| **Role Capability Map** | Links a Frappe Role to a set of capabilities |
| **Role Capability Item** | Child: individual capability within a role map |
| **Role Capability Bundle** | Child: bundle reference within a role map |
| **User Capability Item** | Child: capability within a user assignment |
| **User Capability Bundle** | Child: bundle within a user assignment |
| **Permission Group** | Named group of users (e.g., "Finance Team") |
| **Permission Group Member** | Child: user within a group |
| **Permission Group Capability** | Child: capability assigned to a group |
| **Permission Group Bundle** | Child: bundle assigned to a group |
| **Field Capability Map** | Restricts field visibility/editability by capability |
| **Action Capability Map** | Restricts document actions by capability |
| **Capability Policy** | Time-bound, condition-based auto-grant/revoke rules |
| **Capability Prerequisite** | Child: prerequisite capability for another |
| **Capability Request** | Workflow for users to request capabilities |
| **Capability Rate Limit** | Limits how often a capability can be used |
| **Capability Snapshot** | Point-in-time snapshot of all user capabilities |
| **CAPS Audit Log** | Immutable audit trail of all capability changes |
| **CAPS Settings** | Global CAPS configuration |
| **CAPS Integration Pack** | Configuration for external app integration |
| **CAPS Site Profile** | Site-level CAPS configuration and metadata |

## Reports

| Report | Purpose |
|--------|---------|
| Capability Coverage | Shows which capabilities are assigned across users |
| User Access Matrix | Matrix view of user × capability assignments |
| CAPS Audit Report | Filtered view of audit log entries |

## Scheduled Tasks

| Schedule | Task |
|----------|------|
| Hourly | `expire_timeboxed_capabilities`, `expire_temp_group_memberships` |
| Daily | `sync_permission_groups`, `cleanup_audit_logs`, `warn_expiring_capabilities`, `apply_policies`, `expire_policies`, `warm_caches` |
| Weekly | `weekly_admin_digest` |

## Integration Points

- **All Apps:** Every app declares `caps_capabilities` and `caps_field_maps` in hooks.py; CAPS reads these at boot and enforces them
- **frappe_visual:** Uses App Map, ERD, Dependency Graph for the capability graph explorer and admin dashboard
- **Frappe Core:** Hooks into `doc_events["*"]` for universal field filtering and write validation; extends boot session
- **ERPNext / HRMS / Custom Apps:** Each app prefixes its capabilities (e.g., `VX_`, `AC_`, `CD_`) and CAPS enforces them transparently
- **Redis:** Heavy use of cache for resolved capabilities; invalidation on any change

## Self-Declared Capabilities (20)

CAPS itself declares 20 capabilities for managing access to its own features, categorized as:
- **Module:** Dashboard, Graph, Compare, Capabilities, Bundles, Role Maps, Groups
- **Action:** Assign, Policies, Requests, Settings, Rate Limits, Integrations, Snapshots, Site Profile
- **Report:** Audit Logs, Reports, Export
- **Field:** Field Maps, Action Maps
