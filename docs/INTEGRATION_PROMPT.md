# CAPS Integration Prompt

> **Copy this entire file** and paste it into any AI assistant conversation when you want to integrate CAPS with a new Frappe application.

---

## PROMPT START

You are integrating the **CAPS** (Capability-Based Access Control System) Frappe app with a target Frappe application. CAPS provides fine-grained, field-level and action-level access control on top of Frappe's built-in role/DocType permissions.

### What CAPS Does

CAPS adds a **capability layer** that controls:
- Which **fields** a user can see (hide, mask as `●●●●●1234`, or make read-only)
- Which **buttons/actions** a user can click (hide or disable)
- Which **features** a user can access (programmatic checks)

**CAPS complements Frappe permissions — it does NOT replace them.** Frappe still controls CRUD on DocTypes. CAPS controls what happens WITHIN allowed DocTypes.

### How to Integrate

You need to create a `caps_setup.py` file in your app that defines:

1. **Capabilities** — Atomic permission tokens with naming format `{category}:{scope}:{detail}`
2. **Capability Bundles** — Groups of capabilities matching job functions
3. **Role Capability Maps** — Bridge from Frappe Roles to CAPS capabilities/bundles
4. **Field Capability Maps** — Link DocType fields to required capabilities
5. **Action Capability Maps** — Link buttons/actions to required capabilities

### Naming Convention for Capabilities

```
field:{DocType}:{fieldname}      — Field-level access
action:{DocType}:{action_id}     — Button/action access
module:{feature}:{detail}        — Module/feature toggle
api:{endpoint}:{detail}          — API endpoint access
custom:{scope}:{detail}          — Custom business logic
```

### Capability Categories (valid values)

`Field`, `Action`, `Workflow`, `Report`, `API`, `Module`, `Custom`

### Required DocType Field Names (IMPORTANT — exact names)

**Capability DocType:**
- `name1` (Data, required) — Capability name, format `{category}:{scope}:{detail}`
- `label` (Data, required) — Human-readable label
- `category` (Select, required) — One of the valid categories
- `scope_doctype` (Link to DocType) — Target DocType
- `scope_field` (Data) — Target field (for Field category)
- `scope_action` (Data) — Target action (for Action category)
- `is_active` (Check, default 1)
- `is_delegatable` (Check, default 0)
- `parent_capability` (Link to Capability) — For hierarchy
- `prerequisites` (Table of Capability Prerequisite) — Hard/soft prerequisites

**Capability Bundle DocType:**
- `label` (Data, required) — Bundle name
- `capabilities` (Table of Capability Bundle Item) — Child: `capability` (Link to Capability)

**Role Capability Map DocType (autoname: field:role):**
- `role` (Link to Role, required, unique)
- `role_capabilities` (Table of Role Capability Item) — Child: `capability` (Link)
- `role_bundles` (Table of Role Capability Bundle) — Child: `bundle` (Link)

**Field Capability Map DocType (autoname: hash):**
- `doctype_name` (Link to DocType, required)
- `fieldname` (Data, required)
- `capability` (Link to Capability, required)
- `behavior` (Select: hide/read_only/mask/custom, required, default "hide")
- `mask_pattern` (Data) — For mask behavior: `{last4}`, `{first3}`, `***`
- `priority` (Int, default 0) — Higher wins conflicts

**Action Capability Map DocType (autoname: hash):**
- `doctype_name` (Link to DocType, required)
- `action_id` (Data, required) — Button label text
- `action_type` (Select: button/menu_item/workflow_action/print_format/custom)
- `capability` (Link to Capability, required)
- `behavior` (Select: hide/disable/redirect, default "hide")

**User Capability DocType (autoname: field:user):**
- `user` (Link to User, required, unique)
- `direct_capabilities` (Table of User Capability Item) — Child: `capability` (Link), `expires_on` (Datetime)
- `direct_bundles` (Table of User Capability Bundle) — Child: `bundle` (Link), `expires_on` (Datetime)

### caps_setup.py Template

```python
"""
CAPS Integration — {YourApp} Capabilities
==========================================
Registers capabilities, bundles, field maps, action maps, and role maps.
Idempotent — safe to call multiple times.

Call: bench --site {site} execute {yourapp}.setup.caps_setup.register_all
Wire: after_install = "{yourapp}.setup.caps_setup.register_all"  (in hooks.py)
"""

import frappe

def register_all():
    """Master registration — idempotent."""
    _create_capabilities()
    _create_bundles()
    _create_role_maps()
    _create_field_maps()
    _create_action_maps()
    frappe.db.commit()

def _create_capabilities():
    """Create all capability definitions."""
    caps = [
        # Field capabilities
        {"name1": "field:Lead:phone", "label": "View Lead Phone", "category": "Field",
         "scope_doctype": "Lead", "scope_field": "phone", "is_delegatable": 0},
        # Action capabilities
        {"name1": "action:SalesOrder:approve", "label": "Approve Sales Order", "category": "Action",
         "scope_doctype": "Sales Order", "scope_action": "approve", "is_delegatable": 1},
        # Module capabilities
        {"name1": "module:reports:advanced", "label": "Advanced Reports", "category": "Module"},
    ]
    for cap in caps:
        if not frappe.db.exists("Capability", cap["name1"]):
            frappe.get_doc({"doctype": "Capability", "is_active": 1, **cap}).insert(ignore_permissions=True)

def _create_bundles():
    """Create capability bundles for job functions."""
    bundles = {
        "Agent Bundle": ["field:Lead:phone", "module:reports:basic"],
        "Manager Bundle": ["field:Lead:phone", "action:SalesOrder:approve", "module:reports:advanced"],
    }
    for label, cap_list in bundles.items():
        if not frappe.db.exists("Capability Bundle", {"label": label}):
            frappe.get_doc({
                "doctype": "Capability Bundle",
                "label": label,
                "capabilities": [{"capability": c} for c in cap_list if frappe.db.exists("Capability", c)],
            }).insert(ignore_permissions=True)

def _create_role_maps():
    """Map Frappe roles to CAPS bundles."""
    role_maps = {
        "Sales User": {"bundles": ["Agent Bundle"]},
        "Sales Manager": {"bundles": ["Manager Bundle"]},
    }
    for role, config in role_maps.items():
        if not frappe.db.exists("Role Capability Map", role):
            frappe.get_doc({
                "doctype": "Role Capability Map",
                "role": role,
                "role_bundles": [{"bundle": b} for b in config.get("bundles", [])
                                  if frappe.db.exists("Capability Bundle", {"label": b})],
            }).insert(ignore_permissions=True)

def _create_field_maps():
    """Create field-level restrictions."""
    maps = [
        {"doctype_name": "Lead", "fieldname": "phone", "capability": "field:Lead:phone",
         "behavior": "mask", "mask_pattern": "{last4}"},
        {"doctype_name": "Lead", "fieldname": "email_id", "capability": "field:Lead:email",
         "behavior": "hide"},
    ]
    for m in maps:
        if not frappe.db.exists("Field Capability Map",
                                {"doctype_name": m["doctype_name"], "fieldname": m["fieldname"]}):
            frappe.get_doc({"doctype": "Field Capability Map", **m}).insert(ignore_permissions=True)

def _create_action_maps():
    """Create action-level restrictions."""
    maps = [
        {"doctype_name": "Sales Order", "action_id": "Approve", "action_type": "button",
         "capability": "action:SalesOrder:approve", "behavior": "hide"},
    ]
    for m in maps:
        if not frappe.db.exists("Action Capability Map",
                                {"doctype_name": m["doctype_name"], "action_id": m["action_id"]}):
            frappe.get_doc({"doctype": "Action Capability Map", **m}).insert(ignore_permissions=True)
```

### Server-Side Usage in Your App

```python
# Guard an action (throws PermissionError if denied)
from caps.utils.resolver import require_capability
require_capability("action:SalesOrder:approve")

# Conditional check (returns bool)
from caps.utils.resolver import check_capability
if check_capability("module:reports:advanced"):
    return advanced_report()

# Check any of multiple capabilities
from caps.utils.resolver import check_any_capability
if check_any_capability(["admin:all", "reports:export"]):
    allow_export()
```

### Client-Side Usage in Your App

```javascript
// Conditional button
frappe.caps.ifCan("action:SalesOrder:approve", () => {
    frm.add_custom_button(__("Approve"), approve_handler);
});

// Async check
frappe.caps.check("module:reports:advanced").then(has_it => {
    if (has_it) show_advanced_tab();
});
```

### hooks.py Additions for Your App

```python
# Wire caps_setup to install
after_install = "{yourapp}.setup.caps_setup.register_all"

# Optional: Add CAPS doc event handlers for your DocTypes
doc_events = {
    "Lead": {
        "on_load": "caps.hooks_integration.auto_filter_fields",      # Already wired globally
        "before_save": "caps.hooks_integration.auto_validate_writes", # Already wired globally
    }
}
# NOTE: The wildcard hooks are already wired globally by CAPS.
# You only need explicit hooks if you want additional custom behavior.
```

### Testing Pattern

```python
_TEST_PREFIX = "myapptest_"

def _setup():
    frappe.get_doc({
        "doctype": "Capability",
        "name1": f"{_TEST_PREFIX}field:Lead:phone",
        "label": "Test View Phone",
        "category": "Field",
        "is_active": 1,
    }).insert(ignore_permissions=True)

    frappe.get_doc({
        "doctype": "Field Capability Map",
        "doctype_name": "Lead",
        "fieldname": "phone",
        "capability": f"{_TEST_PREFIX}field:Lead:phone",
        "behavior": "hide",
    }).insert(ignore_permissions=True)

    frappe.get_doc({
        "doctype": "User Capability",
        "user": f"{_TEST_PREFIX}user@test.local",
        "direct_capabilities": [
            {"capability": f"{_TEST_PREFIX}field:Lead:phone"}
        ],
    }).insert(ignore_permissions=True)
```

### Key Behaviors to Know

1. **Zero-code enforcement**: Once Field/Action Maps exist, CAPS automatically enforces them on ALL DocTypes via wildcard `doc_events["*"]`
2. **Resolution is cached**: Changes take up to `cache_ttl` seconds (default 300s) to propagate
3. **4 resolution channels**: Direct + Groups + Roles + Hierarchy (OR-union, then prerequisites enforced)
4. **Client auto-hooks**: `frappe.caps.enforce(frm)` runs on every form refresh automatically
5. **Admin bypass**: Administrator gets all capabilities when `admin_bypass` is enabled (default)

### Your Task

Given the target app's DocTypes and roles, create a `caps_setup.py` that:
1. Defines capabilities for all sensitive fields and restricted actions
2. Creates bundles matching the app's job functions/roles
3. Maps Frappe roles to appropriate bundles
4. Creates field maps for fields that need restriction (with appropriate behaviors)
5. Creates action maps for buttons/actions that need restriction
6. Is fully idempotent (check exists before create)

## PROMPT END
