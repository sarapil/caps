# Screen Designs — تصاميم الشاشات

This directory contains visual screen design specifications for **CAPS** (Capability-Based Access Control System).

## Design Standards

Every screen MUST comply with:

- At least 1 `frappe_visual` component
- At least 3 `.fv-fx-*` CSS effect classes
- GSAP entrance animation (stagger on cards/items)
- CSS Logical Properties (no `margin-left`, use `margin-inline-start`)
- Dark mode compatible (CSS variables only)
- RTL support with CSS Logical Properties
- Responsive: 320px → 4K
- Contextual help (❓) button linked to arkan_help

## Screen Index

| Screen                    | File                                                 | Primary Role   | Serves Scenarios                 |
| ------------------------- | ---------------------------------------------------- | -------------- | -------------------------------- |
| **Dashboard**             | [dashboard.md](dashboard.md)                         | Admin, Manager | DS-001, CR-001, CR-005           |
| **Capability Management** | [capability-management.md](capability-management.md) | Admin          | DS-002 (Admin), WS-002 (Manager) |
| **Permission Group**      | [permission-group.md](permission-group.md)           | Admin, Manager | DS-003, CR-003                   |

## Planned Screens (stub placeholders)

| Screen                    | Status     |
| ------------------------- | ---------- |
| `capability-requests.md`  | ⏳ Planned |
| `user-capability-form.md` | ⏳ Planned |
| `my-capabilities.md`      | ⏳ Planned |
| `audit-report.md`         | ⏳ Planned |
| `capability-policy.md`    | ⏳ Planned |
| `delegation-form.md`      | ⏳ Planned |
| `graph-explorer.md`       | ⏳ Planned |

## Responsive Matrix

See [responsive-matrix.md](responsive-matrix.md) for breakpoint behavior across all screens.

## frappe_visual Components Used

Primary components from frappe_visual used in CAPS screens:

| Component              | Usage                               |
| ---------------------- | ----------------------------------- |
| `scenePresetOffice`    | Dashboard header with animated KPIs |
| `sceneDataBinder`      | Live data binding for scene frames  |
| `DataCard`             | KPI summary cards                   |
| `Sparkline`            | 7-day trend mini-charts             |
| `VisualFormDashboard`  | Form stats ribbon                   |
| `RelationshipExplorer` | Capability hierarchy visualization  |
| `KanbanBoard`          | Permission group member management  |
| `TreeView`             | Group hierarchy                     |
| `NotificationStack`    | Alert banners                       |
| `StatusBadge`          | Active/Inactive indicators          |

## CSS Effect Classes

Required classes from frappe_visual:

```css
.fv-fx-glass           /* Glassmorphism with backdrop-blur */
.fv-fx-hover-lift      /* Lift on hover with shadow */
.fv-fx-page-enter      /* Fade + slide-up entrance */
.fv-fx-gradient-text   /* Gradient-colored text */
.fv-fx-hover-shine     /* Shine sweep on hover */
.fv-fx-mouse-glow      /* Dynamic cursor-following glow */
```

## Creating New Screen Specs

1. Copy template from existing screen spec
2. Fill in all required sections:
   - Screen Overview (route, users, scenarios, devices)
   - Visual Design (components, effects, animations)
   - Layout Structure (ASCII diagram)
   - Responsive Behavior table
   - Configuration code snippets
   - Dark mode / RTL support notes
   - Contextual help integration
   - Accessibility requirements
   - Actions and permissions
