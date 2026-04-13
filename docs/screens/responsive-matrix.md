# Responsive Matrix — مصفوفة الاستجابة

## Breakpoints — نقاط التوقف

| Breakpoint | Width | Layout | Arabic |
|-----------|-------|--------|--------|
| **Mobile S** | 320px – 479px | Single column, minimal UI | عمود واحد، واجهة مختصرة |
| **Mobile L** | 480px – 767px | Single column, bottom actions | عمود واحد، إجراءات سفلية |
| **Tablet** | 768px – 1023px | Two column, collapsible sidebar | عمودان، شريط جانبي قابل للطي |
| **Desktop** | 1024px – 1439px | Full layout with sidebar | تخطيط كامل مع الشريط الجانبي |
| **Large** | 1440px+ | Extended layout with side panels | تخطيط موسع مع ألواح جانبية |

## Per-Screen Behavior — سلوك كل شاشة

| Screen | Mobile | Tablet | Desktop | Large |
|--------|--------|--------|---------|-------|
| **Dashboard** | ✅ KPI carousel | ✅ 2x2 grid | ✅ 4-col + side panels | ✅ Extended with charts |
| **Graph Explorer** | ⚠️ Limited | ✅ Compact | ✅ Full | ✅ Full + minimap |
| **Capability Form** | ✅ Sections stack | ✅ Sections stack | ✅ Side-by-side | ✅ + relationship explorer |
| **Permission Group** | ✅ Tabs | ✅ Tabs | ✅ Split view | ✅ + member kanban |
| **User Capabilities** | ✅ List | ✅ List | ✅ Table | ✅ Table + filters |
| **Audit Report** | ⚠️ Basic | ✅ Scrollable | ✅ Full filters | ✅ Full + export |
| **Capability Requests** | ✅ Cards | ✅ Cards | ✅ Table | ✅ Table + actions |
| **Policy Config** | ⚠️ Limited | ✅ Form | ✅ Form + preview | ✅ Form + visual |
| **Snapshot Export** | ⚠️ Trigger only | ✅ Basic | ✅ Full | ✅ Full + scheduling |

### Legend
- ✅ Full functionality
- ⚠️ Limited functionality (core actions work, advanced features hidden)
- ❌ Not supported (redirects to tablet/desktop)

## Component Behavior by Breakpoint

### Scene Dashboard
```
Mobile:    sceneDataBinder → Simple number cards (no animated scene)
Tablet:    Simplified scene with 2 frames visible
Desktop+:  Full scenePresetOffice with all frames and navigation
```

### KPI Grid
```
Mobile S:  Single column, 1 card per row
Mobile L:  2 cards per row, smaller values
Tablet:    2x2 grid
Desktop:   4 cards in row
Large:     4 cards + sparklines
```

### Graph Explorer
```
Mobile:    Info banner "Best viewed on larger screen", basic list view
Tablet:    Compact graph with limited interactivity
Desktop:   Full Cytoscape graph with toolbar
Large:     Graph + minimap + detail panel
```

### Forms (Capability, Policy, etc.)
```
Mobile:    Vertical sections, tabs for child tables
Tablet:    Vertical sections, inline child tables
Desktop:   Side-by-side sections, relationship explorer
Large:     Side-by-side + live validation hints
```

### List/Table Views
```
Mobile:    Card view with key fields only
Tablet:    Compact table (limited columns)
Desktop:   Full table with all columns
Large:     Table + inline quick actions
```

## RTL Considerations (Arabic/Urdu/Persian)

All breakpoints support RTL via CSS Logical Properties:
- `margin-inline-start` instead of `margin-left`
- `text-align: start` instead of `text-align: left`
- Grid/flex containers use `direction: rtl` from :root

Specific RTL adjustments:
- Sidebar appears on right
- KPI cards flow right-to-left
- Graph nodes position mirrored
- Navigation arrows swap direction

## Touch Targets

| Element | Min Size | Mobile | Tablet+ |
|---------|----------|--------|---------|
| Buttons | 44×44px | ✅ | ✅ |
| Links | 44×44px | ✅ | ✅ |
| Icons | 24×24px tap area 44×44px | ✅ | ✅ |
| Cards | Full width | Swipeable | Clickable |

## Testing Checklist

For each screen at each breakpoint:
- [ ] All primary actions accessible
- [ ] Text readable without zoom
- [ ] Touch targets meet minimum
- [ ] RTL layout correct
- [ ] Dark mode renders properly
- [ ] Loading states show
- [ ] Error states handle gracefully
