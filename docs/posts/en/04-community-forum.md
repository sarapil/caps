<!-- Post Type: Community Forum | Platform: discuss.frappe.io, GitHub Discussions -->
<!-- Target: Frappe developers and power users -->
<!-- Last Updated: 2026-04-04 -->

# [Announcement] CAPS — Fine-Grained Access Control for Frappe Apps | Open Source

Hi Frappe Community! 👋

We're excited to share **CAPS**, a new open-source security app for Frappe/ERPNext.

## What it does

✅ Capability-Based Permissions
✅ Field-Level Access Control
✅ Role → Job → User Hierarchy
✅ Visual Permission Editor
✅ Permission Audit Trail
✅ Cross-App Permission Management
✅ API Permission Enforcement
✅ Dynamic Permission Rules

## Why we built it

- Frappe's built-in roles are too coarse
- No field-level restrictions out of the box
- Permission changes not auditable
- Complex multi-app permission requirements

We couldn't find a good security solution that integrates natively with ERPNext, so we built one.

## Tech Stack

- **Backend:** Python, Frappe Framework v16
- **Frontend:** JavaScript, Frappe UI, frappe_visual components
- **Database:** MariaDB (standard Frappe)
- **License:** MIT
- **Dependencies:** frappe_visual, caps, arkan_help

## Installation

```bash
bench get-app https://github.com/sarapil/caps
bench --site your-site install-app caps
bench --site your-site migrate
```

## Screenshots

[Screenshots will be added to the GitHub repository]

## Roadmap

We're actively developing and would love community feedback on:
1. What features would you like to see?
2. What integrations are most important?
3. Any bugs or issues you encounter?

## Links

- 🔗 **GitHub:** https://github.com/sarapil/caps
- 📖 **Docs:** https://arkan.it.com/caps/docs
- 🏪 **Marketplace:** Frappe Cloud Marketplace
- 📧 **Contact:** support@arkan.it.com

## About Arkan Lab

We're building a complete ecosystem of open-source business apps for Frappe/ERPNext, covering hospitality, construction, CRM, communications, coworking, and more. All apps are designed to work together seamlessly.

Check out our full portfolio: https://arkan.it.com

---

*Feedback and contributions welcome! Star ⭐ the repo if you find it useful.*
