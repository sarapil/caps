# Permission Group Screen — شاشة مجموعة الأذونات

## Screen Overview

- **Route**: `/desk/Form/Permission Group/{name}`
- **Primary Users**: Admin, Manager
- **Serves Scenarios**: DS-003 (Manager), CR-003
- **Device Targets**: Desktop (Primary), Tablet (Secondary)

## Visual Design

### frappe_visual Components Used

1. `VisualFormDashboard` — Member count and capability stats
2. `KanbanBoard` — Drag-and-drop member management
3. `TreeView` — Group hierarchy visualization
4. `Sortable` — Reorder group capabilities

### CSS Effect Classes (minimum 3)

- `.fv-fx-glass` — Group header card
- `.fv-fx-hover-lift` — Member cards lift on hover
- `.fv-fx-page-enter` — Form entrance animation
- `.fv-fx-mouse-glow` — Subtle glow following cursor on form

### GSAP Animations

- Member avatars fade in with stagger
- Capability badges animate when added/removed
- Tree nodes expand with smooth animation

## Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│  📊 Stats Ribbon                                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │Members:15│ │Caps: 8   │ │Bundles: 2│ │Children:3│       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
├─────────────────────────────────────────────────────────────┤
│  Group: Sales Operations Team                               │
│  Type: Manual    Managed By: Sales Manager                  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────┐  ┌─────────────────────────┐  │
│  │ 👥 Members              │  │ 🌳 Group Hierarchy      │  │
│  │ ┌─────┐ ┌─────┐ ┌─────┐│  │      Sales Org          │  │
│  │ │ Ali │ │Sara │ │Ahmed││  │      ├── Sales Ops ◄    │  │
│  │ └─────┘ └─────┘ └─────┘│  │      │   └── Sub-team   │  │
│  │ [+ Add Member]         │  │      └── Marketing      │  │
│  └─────────────────────────┘  └─────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  Tabs: [Members] [Capabilities] [Bundles] [Settings]       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Members Tab:                                         │   │
│  │ • Drag-drop reorder                                  │   │
│  │ • Bulk add from department                           │   │
│  │ • Set temporary membership (Valid From/Till)        │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Responsive Behavior

| Breakpoint          | Layout Changes                        |
| ------------------- | ------------------------------------- |
| Desktop (>1200px)   | Side-by-side members + hierarchy tree |
| Tablet (768-1200px) | Tabs for members vs hierarchy         |
| Mobile (<768px)     | Full-width member list, tree as modal |

## Member Management

```javascript
// Kanban-style member management
frappe.visual.kanban("#group-members", {
  doctype: "Permission Group Member",
  filters: { parent: frm.doc.name },
  columns: [
    { label: __("Active"), filter: { is_active: 1 } },
    { label: __("Temporary"), filter: { valid_till: ["is", "set"] } },
    {
      label: __("Expired"),
      filter: { valid_till: ["<", frappe.datetime.nowdate()] },
    },
  ],
  cardTemplate: (member) => `
        <div class="member-card fv-fx-hover-lift">
            ${frappe.avatar(member.user)}
            <span>${member.full_name}</span>
            ${member.valid_till ? `<small>Until ${member.valid_till}</small>` : ""}
        </div>
    `,
});
```

## Group Hierarchy Tree

```javascript
frappe.visual.tree("#group-hierarchy", {
  doctype: "Permission Group",
  parent_field: "parent_group",
  root_filters: { parent_group: ["is", "not set"] },
  highlight: frm.doc.name,
  onNodeClick: (node) =>
    frappe.set_route("Form", "Permission Group", node.name),
});
```

## Effective Capabilities Calculation

Shows all capabilities a member receives:

1. Direct group capabilities
2. Bundle capabilities
3. Inherited from parent groups

```
Effective Capabilities for User in Group:
├── Direct (3)
│   └── CAPS_view_dashboard
│   └── CAPS_manage_members
│   └── CAPS_submit_requests
├── From Bundle "Sales Ops" (5)
│   └── SO_create_orders
│   └── SO_view_customers
│   └── ...
└── Inherited from "Sales Org" (2)
    └── SALES_view_reports
    └── SALES_export_data
```

## Dark Mode Support

- Member cards use `var(--card-bg)`
- Tree lines use `var(--border-color)`
- Avatar rings match group color

## RTL Support

- Tree expands from right
- Member cards flow right-to-left
- Action buttons mirror position

## Contextual Help (❓)

- Members section: "Add users who should receive this group's capabilities"
- Hierarchy section: "Children groups inherit parent's capabilities"

## Sync Options (for Auto-Sync groups)

| Sync Source  | Query                  | Frequency    |
| ------------ | ---------------------- | ------------ |
| Department   | `department = "Sales"` | Daily        |
| Branch       | `branch = "Dubai"`     | Daily        |
| Custom Query | SQL or Frappe filters  | Configurable |

## Actions

| Action       | Permission         | Effect                      |
| ------------ | ------------------ | --------------------------- |
| Save         | CAPS Admin/Manager | Saves group definition      |
| Sync Members | CAPS Admin         | Runs sync query immediately |
| Clone Group  | CAPS Admin         | Creates copy with new name  |
| View Members | CAPS Manager       | Opens member list view      |
