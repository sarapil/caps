# CAPS Developer Guide

How to integrate CAPS with your Frappe application.

---

## Table of Contents

1. [Quick Integration](#quick-integration)
2. [Defining Capabilities](#defining-capabilities)
3. [Field-Level Restrictions](#field-level-restrictions)
4. [Action-Level Restrictions](#action-level-restrictions)
5. [Server-Side Checks](#server-side-checks)
6. [Client-Side Checks](#client-side-checks)
7. [Bulk Registration (caps_setup.py pattern)](#bulk-registration)
8. [Testing with CAPS](#testing-with-caps)
9. [Advanced Patterns](#advanced-patterns)

---

## Quick Integration

### Step 1: Define Capabilities

Create a `caps_setup.py` in your app that registers capabilities, bundles, field maps, and action maps:

```python
# myapp/setup/caps_setup.py
import frappe

def register_all():
    """Register all CAPS capabilities for MyApp."""
    _create_capabilities()
    _create_bundles()
    _create_field_maps()
    _create_action_maps()
    _create_role_maps()

def _create_capabilities():
    caps = [
        {"name1": "field:Lead:phone", "label": "View Lead Phone", "category": "Field",
         "scope_doctype": "Lead", "scope_field": "phone"},
        {"name1": "action:SalesOrder:approve_discount", "label": "Approve Discount", "category": "Action",
         "scope_doctype": "Sales Order", "scope_action": "approve_discount"},
        {"name1": "module:reports:advanced", "label": "Advanced Reports", "category": "Module"},
    ]
    for cap in caps:
        if not frappe.db.exists("Capability", cap["name1"]):
            doc = frappe.get_doc({"doctype": "Capability", "is_active": 1, **cap})
            doc.insert(ignore_permissions=True)
    frappe.db.commit()
```

### Step 2: Create Field/Action Maps

```python
def _create_field_maps():
    maps = [
        {"doctype_name": "Lead", "fieldname": "phone", "capability": "field:Lead:phone", "behavior": "mask",
         "mask_pattern": "{last4}"},
        {"doctype_name": "Lead", "fieldname": "email_id", "capability": "field:Lead:email", "behavior": "hide"},
    ]
    for m in maps:
        exists = frappe.db.exists("Field Capability Map", {
            "doctype_name": m["doctype_name"], "fieldname": m["fieldname"]
        })
        if not exists:
            frappe.get_doc({"doctype": "Field Capability Map", **m}).insert(ignore_permissions=True)
    frappe.db.commit()
```

### Step 3: Wire into Install

```python
# myapp/hooks.py
after_install = "myapp.setup.caps_setup.register_all"
```

**That's it!** CAPS will automatically enforce field restrictions on all DocTypes.

---

## Defining Capabilities

### Naming Convention

Capability names follow the format: `{category}:{scope}:{detail}`

```
field:Lead:phone          — Field-level: phone on Lead
field:Customer:tax_id     — Field-level: tax_id on Customer
action:SO:approve         — Action: approve button on Sales Order
module:reports:advanced    — Module-level: advanced reports feature
api:export:leads          — API-level: lead export endpoint
custom:crm:vip_access     — Custom: VIP customer access
```

### Categories

| Category | Use For |
|----------|---------|
| `Field` | Field-level access (hide, mask, read_only) |
| `Action` | Button/menu item access |
| `Workflow` | Workflow action gating |
| `Report` | Report visibility |
| `API` | API endpoint access |
| `Module` | Feature/module toggle |
| `Custom` | Anything else |

### Hierarchy

Capabilities can have a `parent_capability` to form a hierarchy:

```python
# Parent capability
{"name1": "crm:all", "label": "Full CRM Access", "category": "Custom"}

# Children — automatically granted when parent is held
{"name1": "crm:read", "label": "CRM Read", "category": "Custom", "parent_capability": "crm:all"}
{"name1": "crm:write", "label": "CRM Write", "category": "Custom", "parent_capability": "crm:all"}
```

### Prerequisites

Capabilities can require other capabilities:

```python
cap = frappe.get_doc({
    "doctype": "Capability",
    "name1": "action:SO:approve",
    "label": "Approve Sales Orders",
    "category": "Action",
    "prerequisites": [
        {"prerequisite": "module:sales:access", "is_hard": 1}
    ]
})
```

If the prerequisite is missing, the capability is removed during resolution.

---

## Field-Level Restrictions

### Behaviors

| Behavior | Effect |
|----------|--------|
| `hide` | Field value set to `None` server-side, hidden in UI |
| `read_only` | Value visible but not editable |
| `mask` | Value masked (e.g., `●●●●●1234`), not editable |
| `custom` | Custom JS handler executed |

### Mask Patterns

| Pattern | Example Input | Output |
|---------|---------------|--------|
| `{last4}` | `+1-555-1234` | `●●●●●1234` |
| `{first3}` | `john@example.com` | `joh●●●●●●●●●●●` |
| `***` | `Secret Value` | `***` |
| (empty) | `Any Value` | `●●●●●●●●` |

### Creating Field Maps

```python
frappe.get_doc({
    "doctype": "Field Capability Map",
    "doctype_name": "Lead",           # Target DocType
    "fieldname": "phone",             # Target field
    "capability": "field:Lead:phone", # Required capability
    "behavior": "mask",               # What happens without the cap
    "mask_pattern": "{last4}",        # For mask behavior
    "priority": 10,                   # Higher = wins conflicts
}).insert(ignore_permissions=True)
```

### How It Works (Zero-Code)

1. User opens a Lead form
2. `hooks_integration.auto_filter_fields()` fires (wildcard `on_load`)
3. Gets user's capabilities via `resolve_capabilities()`
4. Gets field restrictions via `get_field_restrictions("Lead", user)`
5. For each restricted field, applies behavior (hide/mask/read_only)
6. On the client, `frappe.caps.enforce(frm)` applies UI changes

**No code needed in your DocType controller!**

---

## Action-Level Restrictions

### Creating Action Maps

```python
frappe.get_doc({
    "doctype": "Action Capability Map",
    "doctype_name": "Sales Order",
    "action_id": "approve_discount",
    "action_type": "button",            # button, menu_item, workflow_action
    "capability": "action:SO:approve",
    "behavior": "hide",                 # hide or disable
}).insert(ignore_permissions=True)
```

### Client-Side Enforcement

The `caps_controller.js` automatically hides/disables buttons matching the `action_id` label text on every form refresh.

---

## Server-Side Checks

### Guard Functions (Throw on Failure)

```python
from caps.utils.resolver import require_capability

@frappe.whitelist()
def export_leads():
    require_capability("api:export:leads")  # Throws PermissionError
    # ... export logic
```

### Check Functions (Boolean)

```python
from caps.utils.resolver import check_capability, check_any_capability

@frappe.whitelist()
def get_report_data():
    if check_capability("module:reports:advanced"):
        return get_advanced_report()
    else:
        return get_basic_report()

# Check if user has ANY of these capabilities
if check_any_capability(["admin:all", "reports:export"]):
    show_export_button()
```

### Direct Resolution

```python
from caps.utils.resolver import resolve_capabilities

caps = resolve_capabilities("user@example.com")
if "custom:vip:access" in caps:
    # Show VIP features
```

---

## Client-Side Checks

### `frappe.caps.check(capability)` — Async Check

```javascript
frappe.caps.check("module:reports:advanced").then(has_it => {
    if (has_it) {
        // show advanced options
    }
});
```

### `frappe.caps.checkAny(capabilities)` — Any of List

```javascript
frappe.caps.checkAny(["admin:all", "reports:export"]).then(has_any => {
    if (has_any) frm.add_custom_button("Export", handler);
});
```

### `frappe.caps.ifCan(capability, callback)` — Conditional Execution

```javascript
frappe.caps.ifCan("action:SO:approve", () => {
    frm.add_custom_button(__("Approve"), () => approve_handler());
});
```

### `frappe.caps.enforce(frm)` — Full Form Enforcement

Called automatically on every form refresh. You can also call it manually:

```javascript
frappe.ui.form.on("My DocType", {
    refresh(frm) {
        frappe.caps.enforce(frm);  // Already auto-called, but safe to call again
    }
});
```

### `frappe.caps.refreshCapabilities()` — Force Refresh

```javascript
// After admin changes, force refresh from server
frappe.caps.refreshCapabilities().then(() => {
    frappe.caps.enforce(cur_frm);
});
```

---

## Bulk Registration

Follow the AuraCRM pattern (`auracrm/setup/caps_setup.py`) for registering all CAPS data at install time:

```python
def register_all():
    """Idempotent registration — safe to call multiple times."""
    _create_capabilities()    # 80+ capabilities
    _create_bundles()          # 5 job-function bundles
    _create_role_maps()        # Map Frappe roles → bundles
    _create_field_maps()       # Field restrictions per DocType
    _create_action_maps()      # Action restrictions per DocType
    frappe.db.commit()

# Wire in hooks.py:
after_install = "myapp.setup.caps_setup.register_all"
```

Each function should be **idempotent** — check `frappe.db.exists()` before creating.

---

## Testing with CAPS

### Test Utilities

```python
import frappe
import unittest

class TestMyFeature(unittest.TestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        # Clear caches
        frappe.cache.delete_value("caps:user:test@example.com")

    def test_restricted_user_cant_see_phone(self):
        frappe.set_user("test@example.com")
        from caps.overrides import filter_response_fields

        doc = frappe.get_doc("Lead", "LEAD-001")
        filter_response_fields(doc)
        self.assertIsNone(doc.phone)  # Hidden

    def test_capable_user_can_see_phone(self):
        # Grant capability
        frappe.get_doc({
            "doctype": "User Capability",
            "user": "test@example.com",
            "direct_capabilities": [{"capability": "field:Lead:phone"}]
        }).insert(ignore_permissions=True)

        frappe.set_user("test@example.com")
        from caps.overrides import filter_response_fields

        doc = frappe.get_doc("Lead", "LEAD-001")
        filter_response_fields(doc)
        self.assertIsNotNone(doc.phone)  # Visible
```

### Test Prefixing Convention

Use a unique prefix for test data to avoid conflicts:

```python
_TEST_PREFIX = "mytest_"
_CAPS = {"view_phone": f"{_TEST_PREFIX}field:Lead:phone"}
_USERS = {"agent": f"{_TEST_PREFIX}agent@test.local"}
```

---

## Advanced Patterns

### Permission Groups with Auto-Sync

```python
frappe.get_doc({
    "doctype": "Permission Group",
    "group_name": "Sales Team",
    "sync_type": "Department Sync",
    "sync_source": "Sales",
    "sync_frequency": "Realtime",
    "group_capabilities": [{"capability": "crm:sales:access"}],
    "group_bundles": [{"bundle": "Sales Agent Bundle"}],
}).insert(ignore_permissions=True)
```

Users in the "Sales" department are automatically synced.

### Time-Bound Policies

```python
frappe.get_doc({
    "doctype": "Capability Policy",
    "policy_name": "Holiday Season Access",
    "is_active": 1,
    "scope_type": "Role",
    "scope_role": "Sales Agent",
    "target_capability": "action:SO:approve_discount",
    "grant_type": "Capability",
    "valid_from": "2026-12-01 00:00:00",
    "valid_to": "2026-12-31 23:59:59",
}).insert(ignore_permissions=True)
```

CAPS automatically applies and expires this policy based on the schedule.

### Impersonation for Debugging

```python
from caps.api_impersonation import start_impersonation, stop_impersonation

# Admin can debug another user's view
start_impersonation("problematic_user@company.com")
# Now all capability checks resolve as that user
# Orange banner shown in UI
stop_impersonation()
```

### Snapshots for Auditing

```python
from caps.api_snapshots import take_snapshot, compare_with_current

# Before making changes
take_snapshot(user="user@company.com", label="Before role change")

# Make changes...

# Compare
diff = compare_with_current(snapshot="hash_from_above")
print(diff)  # Shows added/removed capabilities
```
