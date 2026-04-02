/**
 * CAPS Onboarding — Storyboard Walkthrough
 * ══════════════════════════════════════════════════════════════
 * Comprehensive guided tour with persona-based paths:
 *   مدير IT | مدير أمن معلومات | مدير نظام ERPNext | مدقق
 * Uses: Storyboard, GraphEngine, FloatingWindow, VisualDashboard
 */
frappe.pages["caps-onboarding"].on_page_load = async function (wrapper) {
const page = frappe.ui.make_app_page({
parent: wrapper,
title: __("CAPS Onboarding"),
single_column: true,
});

page.set_secondary_action(__("Skip to Dashboard"), () => {
frappe.set_route("caps-admin");
});

const $container = $(page.body).html(frappe.render_template("caps_onboarding"))
.find("#caps-onboarding-container");

// Load visual engine
await frappe.visual.engine();

// Register CAPS types
const defs = {
capability: { palette: "emerald", icon: "🔑", shape: "roundrectangle" },
bundle:     { palette: "violet",  icon: "📦", shape: "octagon" },
group:      { palette: "blue",    icon: "👥", shape: "ellipse" },
role:       { palette: "amber",   icon: "🛡️", shape: "diamond" },
user:       { palette: "indigo",  icon: "👤", shape: "ellipse" },
policy:     { palette: "pink",    icon: "📜", shape: "roundrectangle" },
field_map:  { palette: "teal",    icon: "📝", shape: "roundrectangle" },
action_map: { palette: "orange",  icon: "⚡", shape: "roundrectangle" },
};
for (const [n, d] of Object.entries(defs)) {
frappe.visual.ColorSystem.registerNodeType(n, d);
}

// Build storyboard steps
const steps = [
/* ──── Step 1: Welcome ──── */
{
title: __("Welcome to CAPS"),
content: (el) => {
el.innerHTML = `
<div style="text-align:center;padding:20px;">
<img src="/assets/caps/images/caps-logo-animated.svg" style="width:120px;height:120px;margin-bottom:16px;">
<h3 style="color:var(--caps-brand,#10B981);">${__("Capability-Based Access Control")}</h3>
<p style="max-width:500px;margin:12px auto;line-height:1.7;">
${__("CAPS provides enterprise-grade, fine-grained access governance for your Frappe applications. Instead of coarse roles, CAPS lets you define atomic capabilities and compose them into bundles, groups, and policies — fully auditable and compliant.")}
</p>
<div style="margin-top:16px;display:flex;justify-content:center;gap:16px;flex-wrap:wrap;">
<div style="text-align:center;"><span style="font-size:2em;">🔑</span><br><small>${__("Capabilities")}</small></div>
<div style="text-align:center;"><span style="font-size:2em;">📦</span><br><small>${__("Bundles")}</small></div>
<div style="text-align:center;"><span style="font-size:2em;">👥</span><br><small>${__("Groups")}</small></div>
<div style="text-align:center;"><span style="font-size:2em;">📜</span><br><small>${__("Policies")}</small></div>
<div style="text-align:center;"><span style="font-size:2em;">📸</span><br><small>${__("Snapshots")}</small></div>
<div style="text-align:center;"><span style="font-size:2em;">⏱️</span><br><small>${__("Rate Limits")}</small></div>
</div>
</div>
`;
},
},
/* ──── Step 2: Architecture ERD ──── */
{
title: __("System Architecture"),
content: (el) => {
el.innerHTML = `
<p style="margin-bottom:12px;">${__("CAPS has 14 core DocTypes that form a complete access governance framework. Here's how they connect:")}</p>
<div id="onboard-erd" style="height:350px;border:1px solid var(--border-color);border-radius:8px;overflow:hidden;"></div>
`;
setTimeout(() => {
const erd_container = document.getElementById("onboard-erd");
if (!erd_container) return;
new frappe.visual.GraphEngine({
container: erd_container,
nodes: [
{ id: "cap",    label: __("Capability"),       type: "capability", icon: "🔑" },
{ id: "bundle", label: __("Bundle"),           type: "bundle",     icon: "📦" },
{ id: "user",   label: __("User Capability"),  type: "user",       icon: "👤" },
{ id: "group",  label: __("Permission Group"), type: "group",      icon: "👥" },
{ id: "role",   label: __("Role Map"),         type: "role",       icon: "🛡️" },
{ id: "policy", label: __("Policy"),           type: "policy",     icon: "📜" },
{ id: "field",  label: __("Field Map"),        type: "field_map",  icon: "📝" },
{ id: "action", label: __("Action Map"),       type: "action_map", icon: "⚡" },
],
edges: [
{ source: "cap", target: "bundle", label: __("grouped") },
{ source: "cap", target: "user",   label: __("granted") },
{ source: "group", target: "user",   label: __("members") },
{ source: "role", target: "cap",    label: __("maps") },
{ source: "policy", target: "cap",  label: __("auto-grants") },
{ source: "cap", target: "field",   label: __("restricts") },
{ source: "cap", target: "action",  label: __("restricts") },
],
layout: "elk-layered",
minimap: false,
contextMenu: false,
animate: true,
});
}, 400);
},
},
/* ──── Step 3: Choose Your Persona ──── */
{
title: __("What's Your Role?"),
content: `<p style="margin-bottom:12px;">${__("Choose your role to get a tailored walkthrough of CAPS:")}</p>`,
choices: [
{ label: __("🖥️ IT Manager"), value: "it_manager", color: "#10B981", goTo: 3 },
{ label: __("🔐 InfoSec Manager"), value: "infosec", color: "#8B5CF6", goTo: 5 },
{ label: __("🏢 ERPNext Admin"), value: "erpnext_admin", color: "#3B82F6", goTo: 7 },
{ label: __("📋 Auditor"), value: "auditor", color: "#F59E0B", goTo: 9 },
],
},
/* ──── Step 4: IT Manager — System Setup ──── */
{
title: __("IT Manager: System Setup"),
content: (el) => {
el.innerHTML = `
<div style="line-height:1.7;">
<p>${__("As IT Manager, you own the CAPS infrastructure:")}</p>
<ul style="padding-left:18px;">
<li><strong>${__("CAPS Settings")}</strong> — ${__("Configure enforcement mode, cache strategy, fallback behavior")}</li>
<li><strong>${__("Site Profiles")}</strong> — ${__("Manage capability sets per environment (dev/staging/prod)")}</li>
<li><strong>${__("Integration Packs")}</strong> — ${__("Sync CAPS with ERPNext, HRMS, and third-party apps")}</li>
<li><strong>${__("Rate Limits")}</strong> — ${__("Set per-capability rate limits to prevent system abuse")}</li>
<li><strong>${__("Admin Dashboard")}</strong> — ${__("Real-time stats on capability utilization and system health")}</li>
</ul>
<p style="margin-top:12px;"><a href="/app/caps-settings">${__("Go to CAPS Settings →")}</a></p>
</div>
`;
},
},
/* ──── Step 5: IT Manager — Graph Explorer ──── */
{
title: __("IT Manager: Visual Graph Explorer"),
content: (el) => {
el.innerHTML = `
<div style="line-height:1.7;">
<p>${__("The Graph Explorer gives you a complete topology of your CAPS configuration:")}</p>
<ul style="padding-left:18px;">
<li><strong>${__("Hierarchy")}</strong> — ${__("Parent→child capability relationships")}</li>
<li><strong>${__("Prerequisites")}</strong> — ${__("Hard/soft dependency chains between capabilities")}</li>
<li><strong>${__("Bundles")}</strong> — ${__("Which capabilities form each bundle")}</li>
<li><strong>${__("Role Maps")}</strong> — ${__("How Frappe roles map to CAPS capabilities")}</li>
<li><strong>${__("Groups")}</strong> — ${__("Permission group tree structure with inheritance")}</li>
</ul>
<p>${__("Click nodes for details. Double-click to navigate. Export as SVG or PNG.")}</p>
<p style="margin-top:12px;"><a href="/app/caps-graph">${__("Open Graph Explorer →")}</a></p>
</div>
`;
},
},
/* ──── Step 6: InfoSec Manager — Policy & Compliance ──── */
{
title: __("InfoSec: Security Policies"),
content: (el) => {
el.innerHTML = `
<div style="line-height:1.7;">
<p>${__("As Information Security Manager, CAPS is your compliance engine:")}</p>
<ul style="padding-left:18px;">
<li><strong>${__("Capability Policies")}</strong> — ${__("Auto-grant/revoke capabilities based on conditions (department, role, time)")}</li>
<li><strong>${__("Field Masking")}</strong> — ${__("Hide cost data, PII, salary fields from unauthorized users")}</li>
<li><strong>${__("Action Gates")}</strong> — ${__("Restrict approve, submit, delete, export actions per capability")}</li>
<li><strong>${__("Time-Boxed Access")}</strong> — ${__("Grant temporary elevated privileges that auto-expire")}</li>
<li><strong>${__("Separation of Duties")}</strong> — ${__("Prevent conflicting capabilities from being co-assigned")}</li>
</ul>
<p style="margin-top:12px;"><a href="/app/capability-policy">${__("Configure Policies →")}</a></p>
</div>
`;
},
},
/* ──── Step 7: InfoSec Manager — Audit & Snapshots ──── */
{
title: __("InfoSec: Audit & Compliance"),
content: (el) => {
el.innerHTML = `
<div style="line-height:1.7;">
<p>${__("Complete audit infrastructure for compliance assurance:")}</p>
<ul style="padding-left:18px;">
<li><strong>${__("Audit Log")}</strong> — ${__("Every capability change timestamped and attributed to a user")}</li>
<li><strong>${__("Compliance Snapshots")}</strong> — ${__("Point-in-time freeze of all user capabilities for regulatory reviews")}</li>
<li><strong>${__("Coverage Report")}</strong> — ${__("Identify unused capabilities and over-privileged users")}</li>
<li><strong>${__("Access Matrix")}</strong> — ${__("Users × capabilities cross-reference for external auditors")}</li>
</ul>
<p style="margin-top:12px;"><a href="/app/caps-audit-log">${__("View Audit Log →")}</a></p>
</div>
`;
},
},
/* ──── Step 8: ERPNext Admin — Role & Bundle Setup ──── */
{
title: __("ERPNext Admin: Roles & Bundles"),
content: (el) => {
el.innerHTML = `
<div style="line-height:1.7;">
<p>${__("As ERPNext System Manager, CAPS bridges Frappe roles to granular business access:")}</p>
<ul style="padding-left:18px;">
<li><strong>${__("Role Capability Map")}</strong> — ${__("Map existing Frappe roles (Accounts User, Sales Manager) to CAPS capabilities")}</li>
<li><strong>${__("Capability Bundles")}</strong> — ${__("Group related capabilities into job function bundles (Accountant, Purchaser)")}</li>
<li><strong>${__("Permission Groups")}</strong> — ${__("Create department/team groups with capability inheritance")}</li>
<li><strong>${__("User Capabilities")}</strong> — ${__("Direct per-user capability assignment for exceptions")}</li>
<li><strong>${__("Delegation")}</strong> — ${__("Grant CAPS Manager role to team leads for decentralized management")}</li>
</ul>
<p style="margin-top:12px;"><a href="/app/role-capability-map">${__("Configure Role Maps →")}</a></p>
</div>
`;
},
},
/* ──── Step 9: ERPNext Admin — Field & Action Maps ──── */
{
title: __("ERPNext Admin: Field & Action Control"),
content: (el) => {
el.innerHTML = `
<div style="line-height:1.7;">
<p>${__("Fine-grained control over what users see and do in ERPNext forms:")}</p>
<ul style="padding-left:18px;">
<li><strong>${__("Field Capability Map")}</strong> — ${__("Mask cost fields, salary data, margin columns per capability")}</li>
<li><strong>${__("Action Capability Map")}</strong> — ${__("Gate Approve, Submit, Amend, Cancel, Export buttons per capability")}</li>
<li><strong>${__("Compare Users")}</strong> — ${__("Side-by-side diff of any two users' capabilities — great for role audits")}</li>
<li><strong>${__("Capability Requests")}</strong> — ${__("Users can self-service request additional capabilities with approval workflow")}</li>
</ul>
<p style="margin-top:12px;"><a href="/app/field-capability-map">${__("Configure Field Maps →")}</a></p>
</div>
`;
},
},
/* ──── Step 10: Auditor — Review Process ──── */
{
title: __("Auditor: Review Process"),
content: (el) => {
el.innerHTML = `
<div style="line-height:1.7;">
<p>${__("As an auditor, CAPS provides comprehensive access verification tools:")}</p>
<ul style="padding-left:18px;">
<li><strong>${__("CAPS Audit Log")}</strong> — ${__("Search by user, capability, date range, action type — complete change history")}</li>
<li><strong>${__("Capability Snapshots")}</strong> — ${__("Compare any two snapshots to detect drift and unauthorized changes")}</li>
<li><strong>${__("User Access Matrix")}</strong> — ${__("Export users × capabilities as CSV/PDF for external audit evidence")}</li>
<li><strong>${__("Coverage Report")}</strong> — ${__("Identify over-assigned capabilities and potential risk areas")}</li>
</ul>
<p style="margin-top:12px;"><a href="/app/query-report/CAPS Audit Report">${__("Open Audit Report →")}</a></p>
</div>
`;
},
},
/* ──── Step 11: Auditor — Compliance Verification ──── */
{
title: __("Auditor: Compliance Checks"),
content: (el) => {
el.innerHTML = `
<div style="line-height:1.7;">
<p>${__("Key compliance verification workflows:")}</p>
<ul style="padding-left:18px;">
<li><strong>${__("Least-Privilege")}</strong> — ${__("Coverage report shows which users have more access than needed")}</li>
<li><strong>${__("Separation of Duties")}</strong> — ${__("Audit log shows if conflicting capabilities were ever co-assigned")}</li>
<li><strong>${__("Temporal Access")}</strong> — ${__("Verify time-boxed capabilities expired on schedule")}</li>
<li><strong>${__("Onboarding/Offboarding")}</strong> — ${__("Trace complete capability grant/revoke cycles per user")}</li>
<li><strong>${__("Incident Response")}</strong> — ${__("Reconstruct exact capabilities a user had at any point in time")}</li>
</ul>
<p style="margin-top:12px;"><a href="/app/capability-snapshot">${__("View Snapshots →")}</a></p>
</div>
`;
},
},
/* ──── Step 12: Completion ──── */
{
title: __("You're All Set!"),
content: (el) => {
el.innerHTML = `
<div style="text-align:center;padding:20px;">
<div style="font-size:4em;margin-bottom:16px;">🎉</div>
<h3>${__("Onboarding Complete!")}</h3>
<p style="max-width:400px;margin:12px auto;line-height:1.7;">
${__("You're ready to use CAPS. Remember, you can always access help by clicking the ❓ icon on any CAPS page.")}
</p>
<div style="margin-top:20px;display:flex;justify-content:center;gap:8px;flex-wrap:wrap;">
<a href="/app/caps-admin" class="btn btn-primary btn-sm">${__("Admin Dashboard")}</a>
<a href="/app/caps-graph" class="btn btn-default btn-sm">${__("Graph Explorer")}</a>
<a href="/app/caps-about" class="btn btn-default btn-sm">${__("Full About Page")}</a>
</div>
</div>
`;
},
},
];

// Create storyboard
frappe.visual.Storyboard.create($container[0], steps, {
onComplete: () => {
frappe.show_alert({ message: __("Onboarding complete! Welcome to CAPS."), indicator: "green" });
},
showProgress: true,
allowSkip: true,
});
};
