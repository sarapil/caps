# Screen Designs — تصاميم الشاشات

This directory contains visual screen design specifications for **Caps**.

## Design Standards

Every screen MUST comply with:
- At least 1 `frappe_visual` component
- At least 3 `.fv-fx-*` CSS effect classes
- GSAP entrance animation
- CSS Logical Properties (no `margin-left`, use `margin-inline-start`)
- Dark mode compatible (CSS variables only)
- RTL support
- Responsive: 320px → 4K

## Screen Index

| Screen | File | Serves Scenarios |
|--------|------|-----------------|
| Dashboard | `dashboard.md` | DS-001 |

## Responsive Matrix

See [responsive-matrix.md](responsive-matrix.md) for breakpoint behavior.
