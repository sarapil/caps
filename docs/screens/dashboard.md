# Dashboard Screen — لوحة التحكم

## Screen Overview

- **Route**: `/desk/caps-admin`
- **Primary Users**: Admin, Manager
- **Serves Scenarios**: DS-001 (Admin), DS-001 (Manager), CR-001, CR-005
- **Device Targets**: Desktop (Primary), Tablet (Secondary), Mobile (Limited)

## Visual Design

### frappe_visual Components Used

1. `scenePresetOffice` — Animated SVG workspace header
2. `sceneDataBinder` — Live KPI data binding
3. `DataCard` — KPI summary cards
4. `Sparkline` — 7-day trend mini-charts
5. `NotificationStack` — Alert banners for pending actions

### CSS Effect Classes (minimum 3)

- `.fv-fx-glass` — Glass morphism on KPI cards
- `.fv-fx-hover-lift` — Cards lift on hover
- `.fv-fx-page-enter` — Fade-in entrance animation
- `.fv-fx-gradient-text` — Gradient on main heading

### GSAP Animations

- Stagger entrance: Cards animate in sequence (0.1s delay each)
- Number ticker: KPI values count up from 0
- Pulse: Pending requests badge pulses when > 0

## Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│  🖼️ Scene Header (scenePresetOffice)                       │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ Active  │ │ Users   │ │ Pending │ │ Policies│           │
│  │ Caps    │ │ 127     │ │ Reqs 5  │ │ Active  │           │
│  │ 48      │ │ ▂▃▅▇    │ │ 🔔      │ │ 12      │           │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────┐  ┌─────────────────────────┐  │
│  │ Quick Actions           │  │ Recent Audit Log        │  │
│  │ • Add Capability        │  │ 10:45 User A → granted  │  │
│  │ • New Permission Group  │  │ 10:32 Policy applied    │  │
│  │ • View Graph Explorer   │  │ 10:15 Request approved  │  │
│  │ • Generate Snapshot     │  │ 09:58 Capability expired│  │
│  └─────────────────────────┘  └─────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Capability Distribution (Donut Chart)               │   │
│  │ [Module: 35%] [Field: 25%] [Action: 20%] [API: 20%]│   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Responsive Behavior

| Breakpoint          | Layout Changes                                 |
| ------------------- | ---------------------------------------------- |
| Desktop (>1200px)   | Full 4-column KPI row, side-by-side panels     |
| Tablet (768-1200px) | 2x2 KPI grid, stacked panels                   |
| Mobile (<768px)     | Single column, KPI carousel, limited audit log |

## Scene Dashboard Configuration

```javascript
const scene = await frappe.visual.scenePresetOffice({
  container: "#caps-dashboard-header",
  theme: "cool",
  frames: [
    { label: __("Active Capabilities"), status: "success" },
    { label: __("Users with Access"), status: "info" },
    { label: __("Pending Requests"), status: "warning" },
    { label: __("Active Policies"), status: "info" },
  ],
});

await frappe.visual.sceneDataBinder({
  engine: scene,
  frames: [
    {
      label: "Active Capabilities",
      doctype: "Capability",
      aggregate: "count",
      filters: { is_active: 1 },
      status_rules: { ">50": "success", "<10": "danger" },
    },
    {
      label: "Pending Requests",
      doctype: "Capability Request",
      aggregate: "count",
      filters: { status: "Pending" },
      status_rules: { ">5": "warning", ">10": "danger" },
    },
  ],
  refreshInterval: 30000,
});
```

## Dark Mode Support

All colors via CSS variables:

- `--caps-primary: #10B981` → `#34D399` in dark
- Card backgrounds: `var(--card-bg)`
- Text: `var(--text-color)`, `var(--text-muted)`

## RTL Support

- CSS Logical Properties used throughout
- Icon positions mirror automatically
- Chart labels support Arabic text

## Contextual Help (❓)

Help button in header opens `/caps-onboarding` in floating window:

```javascript
frappe.visual.floatingWindow({
  url: "/caps-onboarding",
  title: __("CAPS Onboarding"),
  position: "right",
});
```

## Accessibility

- All KPI cards have `aria-label` with full context
- Color is not the only indicator (icons + text)
- Keyboard navigation: Tab through cards, Enter to drill down
- Screen reader: "48 active capabilities, 127 users with access, 5 pending requests"
