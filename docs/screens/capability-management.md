# Capability Management Screen — شاشة إدارة الصلاحيات

## Screen Overview

- **Route**: `/desk/Form/Capability/{name}`
- **Primary Users**: Admin
- **Serves Scenarios**: DS-002 (Admin), WS-002 (Manager)
- **Device Targets**: Desktop (Primary), Tablet (Secondary)

## Visual Design

### frappe_visual Components Used

1. `VisualFormDashboard` — Stats ribbon at form top
2. `RelationshipExplorer` — Shows capability hierarchy and dependencies
3. `KanbanBoard` — For managing capability bundles that include this capability
4. `StatusBadge` — Active/Inactive status indicator

### CSS Effect Classes (minimum 3)

- `.fv-fx-glass` — Form header card
- `.fv-fx-hover-shine` — Action buttons shine on hover
- `.fv-fx-page-enter` — Form slide-in animation
- `.fv-fx-gradient-text` — Capability name heading

### GSAP Animations

- Form sections fade in with stagger (0.15s)
- Save button has success ripple effect
- Relationship graph nodes animate on load

## Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│  📊 Stats Ribbon (VisualFormDashboard)                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │Users: 24 │ │Bundles: 3│ │Policies: 2│ │Deps: 1   │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
├─────────────────────────────────────────────────────────────┤
│  [✓] Active    🏷️ Module Capability                         │
│  CAPS_manage_groups                                         │
│  Description: Manage permission group memberships           │
├─────────────────────────────────────────────────────────────┤
│  ┌────────────────────┐  ┌──────────────────────────────┐  │
│  │ Hierarchy          │  │ 🔗 Relationship Explorer     │  │
│  │ Parent: None       │  │     ┌──────────┐             │  │
│  │ App: caps          │  │     │ This Cap │             │  │
│  │                    │  │     └────┬─────┘             │  │
│  ├────────────────────┤  │ ┌───────┴───────┐           │  │
│  │ Prerequisites      │  │ │Bundle A│Bundle B│          │  │
│  │ • CAPS_view_caps   │  │ └───────┴───────┘           │  │
│  │   (Hard)          │  │                              │  │
│  └────────────────────┘  └──────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  Tabs: [Details] [Prerequisites] [Bundles] [Policies]      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Tab Content Area                                     │   │
│  │ - Details: Basic fields, category, scope            │   │
│  │ - Prerequisites: Child table of required caps       │   │
│  │ - Bundles: Read-only list of bundles containing     │   │
│  │ - Policies: Read-only list of policies granting     │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Responsive Behavior

| Breakpoint          | Layout Changes                                 |
| ------------------- | ---------------------------------------------- |
| Desktop (>1200px)   | Side-by-side hierarchy + relationship explorer |
| Tablet (768-1200px) | Stacked layout, tabs become scrollable         |
| Mobile (<768px)     | Single column, relationship explorer as modal  |

## Form Dashboard Configuration

```javascript
frappe.visual.formDashboard("#capability-dashboard", {
  doctype: "Capability",
  docname: frm.doc.name,
  stats: [
    {
      label: __("Users"),
      doctype: "User Capability",
      filters: { capability: frm.doc.name },
      aggregate: "count",
    },
    {
      label: __("Bundles"),
      doctype: "Capability Bundle Item",
      filters: { capability: frm.doc.name },
      aggregate: "count",
    },
    {
      label: __("Policies"),
      doctype: "Capability Policy",
      filters: { capability: frm.doc.name },
      aggregate: "count",
    },
  ],
});
```

## Relationship Explorer Configuration

```javascript
frappe.visual.relationshipExplorer("#cap-relations", {
  doctype: "Capability",
  docname: frm.doc.name,
  depth: 2,
  directions: ["up", "down"],
  relationTypes: ["parent", "prerequisite", "bundle"],
});
```

## Dark Mode Support

- Form sections use `var(--card-bg)`
- Status badge colors adjust: Active = `#10B981` → `#34D399`
- Graph nodes use theme-aware colors

## RTL Support

- Form labels align to `inline-end`
- Relationship explorer mirrors node positions
- Tab bar scrolls in correct direction

## Contextual Help (❓)

Each section has inline help:

- Hierarchy: "Parent capabilities allow inheritance of permissions"
- Prerequisites: "Hard prerequisites must be granted before this capability"

## Validation Rules

- `capability_name`: Required, unique, format `APP_action_target`
- `category`: Required, one of [Module, Field, Action, Report, API, Custom]
- `scope_doctype`: Required if category is Field or Action

## Actions

| Action     | Permission | Effect                                          |
| ---------- | ---------- | ----------------------------------------------- |
| Save       | CAPS Admin | Saves capability definition                     |
| Activate   | CAPS Admin | Sets is_active = 1                              |
| Deactivate | CAPS Admin | Sets is_active = 0, warns if users affected     |
| View Graph | All        | Opens Graph Explorer focused on this capability |
