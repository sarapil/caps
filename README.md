# 🛡️ CAPS — Capability-Based Access Control System

<p align="center">
  <strong>Fine-grained, domain-agnostic access control for Frappe Framework</strong><br/>
  Version 1.0.0 · Arkan Labs · 286 Tests · 54+ API Endpoints · 22 DocTypes
</p>

<p align="center">
  <a href="https://github.com/ArkanLab/caps/actions/workflows/ci.yml"><img src="https://github.com/ArkanLab/caps/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/ArkanLab/caps/actions/workflows/linters.yml"><img src="https://github.com/ArkanLab/caps/actions/workflows/linters.yml/badge.svg" alt="Linters"></a>
  <img src="https://img.shields.io/badge/Frappe-v16-blue" alt="Frappe v16">
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="MIT License">
  <img src="https://img.shields.io/badge/i18n-Arabic%20%2B%2011%20languages-brightgreen" alt="Multilingual">
</p>

---

## 🎯 What is CAPS?

CAPS is a **Frappe application** that adds capability-based access control **on top of** Frappe's built-in role/permission system. While Frappe controls _which DocTypes_ a user can read/write/create/delete, CAPS controls _which fields they can see_, _which buttons they can click_, and _which features they can use_ — all without writing a single line of code.

> **CAPS complements Frappe permissions — it does NOT replace them.**

### Why CAPS?

| Without CAPS | With CAPS |
|---|---|
| All Sales Agents see all fields on Lead | Junior agents can't see phone numbers (masked as `●●●●●1234`) |
| Anyone with write access can click any button | "Approve Discount" button only shows for managers with that capability |
| Role changes require developer intervention | Admins drag-and-drop capabilities in the UI |
| No audit trail for permission checks | Every check, grant, and revocation is logged |
| Binary roles: you either have it or you don't | Hierarchical capabilities with prerequisites, expiry, and delegation |

---

## 📚 Documentation

| Document | Audience | Description |
|----------|----------|-------------|
| **[README.md](README.md)** | Everyone | Overview, quick start, feature summary |
| **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** | Developers & AI | System design, resolution algorithm, caching strategy |
| **[docs/API_REFERENCE.md](docs/API_REFERENCE.md)** | Developers | Complete API endpoint reference (54+ endpoints) |
| **[docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md)** | Developers | Integration patterns, code examples, extending CAPS |
| **[docs/ADMIN_GUIDE.md](docs/ADMIN_GUIDE.md)** | System Admins | Setup, configuration, policies, troubleshooting |
| **[docs/USER_GUIDE.md](docs/USER_GUIDE.md)** | End Users | Self-service requests, delegation, understanding restrictions |
| **[docs/INTEGRATION_PROMPT.md](docs/INTEGRATION_PROMPT.md)** | AI / Developers | Reusable prompt to integrate CAPS with any Frappe app |
| **[docs/SALES_PITCH.md](docs/SALES_PITCH.md)** | Sales / Clients | Feature showcase for client meetings |
| **[ROADMAP.md](ROADMAP.md)** | Everyone | Completed phases + future plans |
| **[docs/AI_CONTEXT.md](docs/AI_CONTEXT.md)** | AI Models | Complete technical context for AI assistants |

---

## ⚡ Quick Start

```bash
# Install
bench get-app caps
bench --site your-site install-app caps

# Verify
bench --site your-site run-tests --app caps  # 286 tests
```

After installation, two roles are created: **CAPS Admin** and **CAPS Manager**.

### 5-Minute Setup

1. **Enable CAPS** → `CAPS Settings` → ✅ Enable CAPS
2. **Create Capabilities** → `Capability` → e.g., `field:Lead:phone` (hide phone on Lead)
3. **Create Field Maps** → `Field Capability Map` → Link capability to DocType + field
4. **Assign to Users** → Either:
   - **Direct**: `User Capability` → add capabilities per user
   - **By Role**: `Role Capability Map` → map Frappe roles to capabilities
   - **By Group**: `Permission Group` → create groups with shared capabilities
   - **By Bundle**: `Capability Bundle` → group capabilities by job function
5. **Done!** Fields are automatically hidden/masked on next page load.

---

## 🏗️ Core Concepts

```
┌─────────────────────────────────────────────────────────┐
│                    CAPABILITY                            │
│  Atomic permission: "can see phone field on Customer"    │
│  Naming: {category}:{scope}:{detail}                     │
│  Categories: Field, Action, Workflow, Report, API,       │
│              Module, Custom                               │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   ┌─────────┐ ┌──────────┐ ┌──────────────┐
   │ BUNDLE  │ │   ROLE   │ │  PERMISSION  │
   │ Group   │ │   MAP    │ │   GROUP      │
   │ of caps │ │Role→Caps │ │Users+Caps    │
   └────┬────┘ └────┬─────┘ └──────┬───────┘
        │           │              │
        └─────┬─────┘──────────────┘
              ▼
    ┌──────────────────┐
    │ USER CAPABILITY  │
    │  Final resolved  │
    │  capability set  │
    └──────────────────┘
```

### Resolution Algorithm (4 Channels)

CAPS resolves a user's effective capabilities by **unioning** four channels:

1. **Direct** — Capabilities/bundles assigned directly to the user
2. **Groups** — Capabilities from Permission Groups the user belongs to
3. **Roles** — Capabilities mapped to the user's Frappe roles
4. **Hierarchy** — Parent capabilities automatically grant their children

Then: **Prerequisites** are enforced (caps with unmet hard prereqs are removed).

Result is **cached in Redis** per user with configurable TTL (default: 5 minutes).

### Enforcement Layers

| Layer | How | Automatic? |
|-------|-----|-----------|
| **Field Restrictions** | `Field Capability Map` → hide/mask/read_only fields | ✅ Zero-code |
| **Action Restrictions** | `Action Capability Map` → hide/disable buttons | ✅ Zero-code |
| **Server-side** | `auto_filter_fields` / `auto_validate_writes` (wildcard doc_events) | ✅ Automatic |
| **Client-side** | `frappe.caps.enforce(frm)` auto-called on every form refresh | ✅ Automatic |
| **Programmatic** | `require_capability()` / `check_capability()` in Python | Manual |

---

## 🔌 Feature Summary

### Core Features
- ✅ **22 DocTypes** — Capabilities, Bundles, Groups, Maps, Policies, Requests, Snapshots, Audit Logs
- ✅ **4-Channel Resolution** — Direct + Groups + Roles + Hierarchy with prerequisite enforcement
- ✅ **Field-Level Access** — hide, mask (`●●●●●1234`), read_only, custom behaviors
- ✅ **Action-Level Access** — hide/disable buttons, menu items, workflow actions
- ✅ **Zero-Code Enforcement** — Wildcard doc_events automatically enforce on ALL DocTypes
- ✅ **Smart Caching** — Redis per-user + map caches with event-driven invalidation

### Enterprise Features
- ✅ **Capability Policies** — Time-bound, auto-applying rules (by role/department/user list)
- ✅ **Self-Service Requests** — Users request capabilities, managers approve/reject
- ✅ **Delegation** — Managers can delegate their own capabilities to team members
- ✅ **Permission Groups** — Dynamic user groups with auto-sync (Department/Branch/Custom Query)
- ✅ **Capability Hierarchy** — Parent capabilities auto-grant children (multi-level)
- ✅ **Prerequisites** — Capabilities can require other capabilities (with circular dependency detection)

### Admin & Ops
- ✅ **Admin Dashboard** — Stats, user lookup, policies, audit log, expiring grants
- ✅ **Import/Export** — Full config backup/restore as JSON (merge or overwrite)
- ✅ **Capability Snapshots** — Point-in-time capture, diff, and restore
- ✅ **Impersonation** — "View As" mode to debug another user's capability set
- ✅ **Audit Trail** — 16 event types logged with context, IP, timestamps
- ✅ **Expiry Notifications** — Automatic alerts before capabilities expire

### Developer Features
- ✅ **54+ API Endpoints** — 9 API modules with full REST coverage
- ✅ **Client JS Library** — `frappe.caps.check()`, `frappe.caps.enforce(frm)`, `frappe.caps.ifCan()`
- ✅ **Boot Integration** — Capabilities available in `frappe.boot.caps` on every page load
- ✅ **286 Automated Tests** — Comprehensive coverage across all features

---

## 📊 Statistics

| Metric | Count |
|--------|-------|
| DocTypes | 22 (12 parent + 10 child) |
| API Endpoints | 54+ |
| Python Modules | 17 source + 22 controllers |
| Test Methods | 286 |
| JS LOC | ~350 |
| Python LOC | ~11,500+ |
| Scheduled Tasks | 5 (hourly + daily) |
| Cache Keys | 7 types |
| Audit Event Types | 16 |

---

## 🧪 Testing

```bash
# Run all CAPS tests (286 tests)
bench --site dev.localhost run-tests --app caps

# Run specific module
bench --site dev.localhost run-tests --app caps --module caps.tests.test_resolver
bench --site dev.localhost run-tests --app caps --module caps.tests.test_hierarchy
```

### Test Coverage

| Test File | Tests | Area |
|-----------|-------|------|
| test_resolver.py | 44 | Resolution engine, 4 channels, caching |
| test_overrides.py | 24 | Field hide/mask/read_only, write blocking |
| test_settings.py | 22 | Settings validation, kill-switch, defaults |
| test_doctypes.py | 21 | DocType controllers, autoname, validation |
| test_policies.py | 18 | Policy engine, apply/expire/preview |
| test_prerequisites.py | 16 | Prereqs, circular deps, dependency graph |
| test_admin_api.py | 15 | Bulk grant/revoke, clone, trace |
| test_api.py | 14 | Public API: check, batch, grant/revoke |
| test_snapshots.py | 14 | Capture, diff, restore snapshots |
| test_delegation.py | 13 | Delegation workflow |
| test_dashboard.py | 13 | Dashboard analytics endpoints |
| test_transfer.py | 13 | Import/export, round-trip fidelity |
| test_hierarchy.py | 12 | Parent→child inheritance, tree API |
| test_requests.py | 12 | Self-service request workflow |
| test_impersonation.py | 10 | View-as mode |
| test_tasks.py | 7 | Scheduled tasks |
| test_cache_invalidation.py | 6 | Smart cache invalidation |
| test_hooks_integration.py | 6 | Auto-enforcement, login audit |
| test_expiry_notifications.py | 6 | Expiry notifications |
| **Total** | **286** | |

---

## 📦 DocType Reference

### Configuration
| DocType | Purpose |
|---------|---------|
| **CAPS Settings** | Global settings (singleton): enable/disable, cache TTL, audit, delegation |
| **Capability** | Atomic permission definition with category, scope, hierarchy |
| **Capability Bundle** | Named group of capabilities for job functions |

### Assignment
| DocType | Purpose |
|---------|---------|
| **User Capability** | Per-user direct capability/bundle assignments |
| **Role Capability Map** | Map Frappe roles → capabilities/bundles |
| **Permission Group** | Dynamic user groups with shared capabilities |

### Enforcement
| DocType | Purpose |
|---------|---------|
| **Field Capability Map** | DocType.field → capability (hide/mask/read_only) |
| **Action Capability Map** | DocType.action → capability (hide/disable) |

### Enterprise
| DocType | Purpose |
|---------|---------|
| **Capability Policy** | Time-bound auto-applying rules |
| **Capability Request** | Self-service request workflow (Pending→Approved/Rejected) |
| **Capability Snapshot** | Point-in-time capability capture + diff + restore |
| **CAPS Audit Log** | Immutable 16-event-type audit trail |

---

## 🔗 Integration with Other Apps

CAPS is **domain-agnostic** — it works with any Frappe app. See [docs/INTEGRATION_PROMPT.md](docs/INTEGRATION_PROMPT.md) for a complete AI prompt to integrate CAPS with your app.

Quick integration:
```python
# Server-side: guard an action
from caps.utils.resolver import require_capability
require_capability("myapp:feature:export")  # Throws PermissionError if denied

# Server-side: conditional logic
from caps.utils.resolver import check_capability
if check_capability("myapp:reports:advanced"):
    show_advanced_report()
```

```javascript
// Client-side: conditional button
frappe.caps.ifCan("myapp:feature:export", () => {
    frm.add_custom_button("Export", export_handler);
});
```

---

## License

Proprietary — Arkan Labs

## Contact

For support and inquiries:
- Phone: +201508268982
- WhatsApp: https://wa.me/201508268982

