# CAPS Screenshots — صور للمعرض

## Overview

This directory contains screenshots for Frappe Cloud Marketplace listing and documentation.

## Required Screenshots (5+ for Marketplace)

| # | Screenshot | File | Status |
|---|------------|------|--------|
| 1 | **Dashboard Overview** | `01-dashboard.png` | ⏳ Pending |
| 2 | **Graph Explorer** | `02-graph-explorer.png` | ⏳ Pending |
| 3 | **Capability Management** | `03-capability-form.png` | ⏳ Pending |
| 4 | **Permission Groups** | `04-permission-groups.png` | ⏳ Pending |
| 5 | **User Capabilities** | `05-user-capabilities.png` | ⏳ Pending |
| 6 | **Audit Report** | `06-audit-report.png` | ⏳ Pending |
| 7 | **Policy Configuration** | `07-policy-config.png` | ⏳ Pending |

## Screenshot Specifications

- **Resolution**: 1280×800 minimum (2560×1600 preferred for retina)
- **Format**: PNG or WebP
- **Ratio**: 16:10 or 16:9
- **Theme**: Light mode primary, dark mode secondary set
- **Language**: English primary, Arabic set for RTL showcase

## Capture Guidelines

1. **Use demo data** — Never show real customer data
2. **Clear browser** — No bookmarks bar, clean URL bar
3. **Consistent zoom** — 100% browser zoom
4. **Full viewport** — No partial scrollbars unless intentional
5. **Highlight key areas** — Use subtle annotations if needed

## Scene Presets for Screenshots

```javascript
// For consistent dashboard screenshots:
await frappe.visual.scenePresetOffice({
    container: '#caps-dashboard-header',
    theme: 'cool',
    frames: [
        { label: 'Active Capabilities', value: '48', status: 'success' },
        { label: 'Users', value: '127', status: 'info' },
        { label: 'Pending Requests', value: '3', status: 'warning' },
        { label: 'Active Policies', value: '12', status: 'info' }
    ]
});
```

## Marketplace Caption Requirements

Each screenshot needs:
- English caption (40-80 chars)
- Arabic caption (mirror)

### Planned Captions

1. **Dashboard**: "CAPS Dashboard — Real-time capability and request overview" / "لوحة تحكم CAPS — نظرة عامة فورية على الصلاحيات والطلبات"

2. **Graph Explorer**: "Visual Capability Graph — Explore relationships interactively" / "الرسم البياني للصلاحيات — استكشف العلاقات تفاعلياً"

3. **Capability Form**: "Capability Management — Configure atomic permissions" / "إدارة الصلاحيات — تهيئة الأذونات الذرية"

4. **Permission Groups**: "Permission Groups — Organize users and capabilities" / "مجموعات الأذونات — تنظيم المستخدمين والصلاحيات"

5. **User Capabilities**: "User Access View — See exactly who has what" / "عرض وصول المستخدم — اعرف بالضبط من لديه ماذا"

6. **Audit Report**: "Audit Trail — Complete compliance logging" / "مسار التدقيق — تسجيل كامل للامتثال"

7. **Policy Config**: "Policy Engine — Automate capability provisioning" / "محرك السياسات — أتمتة توفير الصلاحيات"

## Automation Script

```bash
# Generate screenshots using Playwright (example)
cd /workspaces/frappe_docker/frappe-bench
bench --site dev.localhost execute caps.utils.screenshot_generator --args "['dashboard']"

# Or use manual capture:
# 1. bench start
# 2. Open http://dev.localhost:8001/desk/caps-admin
# 3. F12 > Device toolbar > Set to 1280x800
# 4. Capture using browser screenshot
```

## Review Checklist

Before submitting to Marketplace:

- [ ] All 7 screenshots captured
- [ ] Light mode versions
- [ ] Dark mode versions (optional but recommended)
- [ ] Arabic RTL versions (at least 2)
- [ ] No PII visible
- [ ] Demo data looks realistic
- [ ] Consistent visual style
- [ ] Captions reviewed for accuracy
