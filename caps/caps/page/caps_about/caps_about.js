// Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
// Developer Website: https://arkan.it.com
// License: MIT
// For license information, please see license.txt

frappe.pages["caps-about"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __("About CAPS"),
        single_column: true,
    });

    const root = $(wrapper).find("#caps-about-root");
    if (!root.length) {
        $(page.body).html('<div id="caps-about-root"></div>');
    }

    render_about_storyboard(page);
};

/* ══════════════════════════════════════════════════════════════ */
/*  14-Slide Storyboard — CAPS About                            */
/*  Tone: أمني / مهني — Enterprise-grade security governance    */
/* ══════════════════════════════════════════════════════════════ */
function render_about_storyboard(page) {
    const BRAND = "#10B981";
    const BRAND_LIGHT = "#D1FAE5";
    const BRAND_DARK = "#065F46";

    const slides = [
        /* ──── 1. Hero Overview ──── */
        {
            title: __("What is CAPS?"),
            icon: "shield-lock",
            content: `
                <div class="caps-about-card">
                    <div class="caps-about-hero">
                        <svg viewBox="0 0 120 120" width="100" height="100">
                            <circle cx="60" cy="60" r="55" fill="${BRAND_LIGHT}" stroke="${BRAND}" stroke-width="3">
                                <animate attributeName="r" values="52;55;52" dur="3s" repeatCount="indefinite"/>
                            </circle>
                            <text x="60" y="68" text-anchor="middle" font-size="36" fill="${BRAND_DARK}" font-weight="bold">🛡️</text>
                        </svg>
                    </div>
                    <h3>${__("Capability-Based Access Control")}</h3>
                    <p>${__("CAPS delivers enterprise-grade, fine-grained access governance for Frappe applications. Move beyond traditional role-based permissions to atomic capability control — every user receives precisely the access they need, fully auditable and compliant.")}</p>
                    <div class="caps-about-features">
                        <div class="caps-feature-chip"><span>🔑</span> ${__("Atomic Capabilities")}</div>
                        <div class="caps-feature-chip"><span>📦</span> ${__("Capability Bundles")}</div>
                        <div class="caps-feature-chip"><span>🔒</span> ${__("Field-Level Masking")}</div>
                        <div class="caps-feature-chip"><span>⚡</span> ${__("Action-Level Gates")}</div>
                        <div class="caps-feature-chip"><span>📋</span> ${__("Policy Engine")}</div>
                        <div class="caps-feature-chip"><span>🕐</span> ${__("Time-Boxed Access")}</div>
                        <div class="caps-feature-chip"><span>📸</span> ${__("Compliance Snapshots")}</div>
                        <div class="caps-feature-chip"><span>⏱️</span> ${__("Rate Limiting")}</div>
                    </div>
                </div>`,
        },
        /* ──── 2. Module Map ──── */
        {
            title: __("Module Map"),
            icon: "sitemap",
            content: `
                <div class="caps-about-card">
                    <p class="text-muted mb-3">${__("Interactive map of all CAPS modules and their relationships — click any node to explore.")}</p>
                    <div id="caps-about-appmap" style="min-height:420px;border:1px solid var(--border-color);border-radius:var(--border-radius-lg);"></div>
                </div>`,
            onShow() {
                if (frappe.visual && frappe.visual.appMap) {
                    frappe.visual.appMap({
                        container: "#caps-about-appmap",
                        app: "caps",
                        interactive: true,
                    });
                } else {
                    $("#caps-about-appmap").html('<p class="text-muted text-center p-5">' + __("Install frappe_visual to see the interactive App Map.") + "</p>");
                }
            },
        },
        /* ──── 3. Entity Relationships ──── */
        {
            title: __("Entity Relationships"),
            icon: "hierarchy-3",
            content: `
                <div class="caps-about-card">
                    <p class="text-muted mb-3">${__("The CAPS data model — 14 interconnected DocTypes forming a complete access governance framework.")}</p>
                    <div id="caps-about-erd" style="min-height:420px;border:1px solid var(--border-color);border-radius:var(--border-radius-lg);"></div>
                </div>`,
            onShow() {
                if (frappe.visual && frappe.visual.erd) {
                    frappe.visual.erd({
                        container: "#caps-about-erd",
                        doctypes: [
                            "Capability", "Capability Bundle", "Role Capability Map",
                            "User Capability", "Permission Group", "Field Capability Map",
                            "Action Capability Map", "Capability Policy", "Capability Request",
                            "Capability Snapshot", "CAPS Settings", "Capability Rate Limit",
                            "CAPS Audit Log", "CAPS Site Profile",
                        ],
                    });
                } else {
                    $("#caps-about-erd").html('<p class="text-muted text-center p-5">' + __("Install frappe_visual to see the ERD.") + "</p>");
                }
            },
        },
        /* ──── 4. Workflow: Access Governance Lifecycle ──── */
        {
            title: __("Workflow: Access Governance Lifecycle"),
            icon: "arrows-right-left",
            content: `
                <div class="caps-about-card">
                    <p class="text-muted mb-3">${__("From capability definition through policy evaluation to runtime enforcement — the complete access governance lifecycle.")}</p>
                    <div id="caps-about-workflow" style="min-height:420px;border:1px solid var(--border-color);border-radius:var(--border-radius-lg);"></div>
                </div>`,
            onShow() {
                if (frappe.visual && frappe.visual.dependencyGraph) {
                    frappe.visual.dependencyGraph({
                        container: "#caps-about-workflow",
                        nodes: [
                            { id: "cap", label: __("Define Capability"), group: "definition" },
                            { id: "bundle", label: __("Group into Bundle"), group: "definition" },
                            { id: "role_map", label: __("Map to Role"), group: "assignment" },
                            { id: "user_cap", label: __("Assign to User"), group: "assignment" },
                            { id: "perm_grp", label: __("Permission Group"), group: "assignment" },
                            { id: "field_map", label: __("Field Restriction"), group: "enforcement" },
                            { id: "action_map", label: __("Action Restriction"), group: "enforcement" },
                            { id: "policy", label: __("Policy Evaluation"), group: "enforcement" },
                            { id: "rate_limit", label: __("Rate Limit Check"), group: "enforcement" },
                            { id: "enforce", label: __("Runtime Enforcement"), group: "enforcement" },
                            { id: "audit", label: __("Audit Trail"), group: "compliance" },
                            { id: "snapshot", label: __("Compliance Snapshot"), group: "compliance" },
                        ],
                        edges: [
                            { source: "cap", target: "bundle" },
                            { source: "bundle", target: "role_map" },
                            { source: "role_map", target: "user_cap" },
                            { source: "user_cap", target: "perm_grp" },
                            { source: "user_cap", target: "field_map" },
                            { source: "user_cap", target: "action_map" },
                            { source: "field_map", target: "policy" },
                            { source: "action_map", target: "policy" },
                            { source: "policy", target: "rate_limit" },
                            { source: "rate_limit", target: "enforce" },
                            { source: "enforce", target: "audit" },
                            { source: "audit", target: "snapshot" },
                        ],
                    });
                } else {
                    $("#caps-about-workflow").html('<p class="text-muted text-center p-5">' + __("Install frappe_visual for workflow visualization.") + "</p>");
                }
            },
        },
        /* ──── 5. Persona: IT Manager (مدير IT) ──── */
        {
            title: __("For IT Managers"),
            icon: "server-cog",
            content: `
                <div class="caps-about-card">
                    <h3>🖥️ ${__("IT Manager — Infrastructure & System Governance")}</h3>
                    <p>${__("As the IT manager, CAPS gives you centralized control over system-wide access policies — from multi-site deployment to integration management.")}</p>
                    <div class="caps-stakeholder-grid">
                        <div class="caps-stakeholder-item">
                            <strong>${__("What you see")}</strong>
                            <ul>
                                <li>${__("CAPS Admin Dashboard — real-time capability utilization metrics")}</li>
                                <li>${__("Site Profile management for multi-tenant deployments")}</li>
                                <li>${__("Integration Pack configuration for ERPNext, HRMS, and third-party apps")}</li>
                                <li>${__("Rate Limit monitoring to prevent system abuse")}</li>
                                <li>${__("Capability Graph Explorer — full system topology")}</li>
                            </ul>
                        </div>
                        <div class="caps-stakeholder-item">
                            <strong>${__("What you do")}</strong>
                            <ul>
                                <li>${__("Define system-wide capabilities and bundles")}</li>
                                <li>${__("Configure CAPS Settings — cache, enforcement mode, fallback behavior")}</li>
                                <li>${__("Manage Site Profiles for different environments (dev/staging/prod)")}</li>
                                <li>${__("Set up Integration Packs to sync capabilities with external systems")}</li>
                                <li>${__("Monitor rate limits and system health via audit logs")}</li>
                            </ul>
                        </div>
                        <div class="caps-stakeholder-item">
                            <strong>${__("How your work connects")}</strong>
                            <ul>
                                <li>${__("InfoSec Manager → receives capability framework you define")}</li>
                                <li>${__("ERPNext Admin → uses bundles and role maps you create")}</li>
                                <li>${__("Auditor → relies on the audit trail and snapshots you configure")}</li>
                            </ul>
                        </div>
                    </div>
                </div>`,
        },
        /* ──── 6. Persona: Information Security Manager (مدير أمن معلومات) ──── */
        {
            title: __("For Information Security Managers"),
            icon: "shield-check",
            content: `
                <div class="caps-about-card">
                    <h3>🔐 ${__("InfoSec Manager — Security Policy & Compliance")}</h3>
                    <p>${__("CAPS is your compliance engine — enforce least-privilege access, implement separation of duties, and maintain a complete audit trail for every access decision.")}</p>
                    <div class="caps-stakeholder-grid">
                        <div class="caps-stakeholder-item">
                            <strong>${__("What you see")}</strong>
                            <ul>
                                <li>${__("Policy Engine dashboard — active policies, condition evaluation logs")}</li>
                                <li>${__("Capability Coverage report — gaps in access control across the system")}</li>
                                <li>${__("User Access Matrix — cross-reference users × capabilities")}</li>
                                <li>${__("Audit Report — full trail of grants, revocations, and escalations")}</li>
                                <li>${__("Compliance Snapshots — point-in-time access state for external audits")}</li>
                            </ul>
                        </div>
                        <div class="caps-stakeholder-item">
                            <strong>${__("What you do")}</strong>
                            <ul>
                                <li>${__("Define Capability Policies — auto-grant/revoke based on conditions")}</li>
                                <li>${__("Configure field masking — hide cost data, PII, or sensitive fields")}</li>
                                <li>${__("Set up action gates — restrict approvals, deletions, exports")}</li>
                                <li>${__("Enforce time-boxed access for temporary elevated privileges")}</li>
                                <li>${__("Schedule periodic Capability Snapshots for compliance reviews")}</li>
                                <li>${__("Review and approve Capability Requests from users")}</li>
                            </ul>
                        </div>
                        <div class="caps-stakeholder-item">
                            <strong>${__("Compliance alignment")}</strong>
                            <ul>
                                <li>${__("Least-privilege enforcement — every user gets minimum needed access")}</li>
                                <li>${__("Separation of duties — conflicting capabilities detected and blocked")}</li>
                                <li>${__("Full audit trail — every grant, revocation, and policy trigger logged")}</li>
                                <li>${__("Periodic attestation via snapshots and coverage reports")}</li>
                            </ul>
                        </div>
                    </div>
                </div>`,
        },
        /* ──── 7. Persona: ERPNext System Manager (مدير نظام ERPNext) ──── */
        {
            title: __("For ERPNext System Managers"),
            icon: "building",
            content: `
                <div class="caps-about-card">
                    <h3>🏢 ${__("ERPNext Admin — Business-Level Access Control")}</h3>
                    <p>${__("Bridge the gap between Frappe roles and real business needs. CAPS lets you control exactly which fields, actions, and workflows each user can access — down to individual form fields.")}</p>
                    <div class="caps-stakeholder-grid">
                        <div class="caps-stakeholder-item">
                            <strong>${__("What you see")}</strong>
                            <ul>
                                <li>${__("Role Capability Maps — how Frappe roles translate to CAPS capabilities")}</li>
                                <li>${__("Field Capability Maps — which fields are visible/masked per capability")}</li>
                                <li>${__("Action Capability Maps — which buttons and workflows are gated")}</li>
                                <li>${__("User Capability assignments — per-user permission profiles")}</li>
                                <li>${__("Permission Groups — team-based capability inheritance")}</li>
                            </ul>
                        </div>
                        <div class="caps-stakeholder-item">
                            <strong>${__("What you do")}</strong>
                            <ul>
                                <li>${__("Map Frappe roles to CAPS capabilities via Role Capability Map")}</li>
                                <li>${__("Build Capability Bundles for common job functions (Accountant, Sales Manager, etc.)")}</li>
                                <li>${__("Configure field restrictions — mask cost, salary, margin data per role")}</li>
                                <li>${__("Gate actions — approve, submit, amend, export restricted by capability")}</li>
                                <li>${__("Create Permission Groups for departments, teams, branches")}</li>
                                <li>${__("Delegate capability management to team leads via CAPS Manager role")}</li>
                            </ul>
                        </div>
                        <div class="caps-stakeholder-item">
                            <strong>${__("Business value")}</strong>
                            <ul>
                                <li>${__("No more over-privileged users with System Manager role")}</li>
                                <li>${__("Granular control without creating dozens of custom roles")}</li>
                                <li>${__("Self-service capability requests reduce IT bottleneck")}</li>
                                <li>${__("Visual graph explorer makes complex permissions understandable")}</li>
                            </ul>
                        </div>
                    </div>
                </div>`,
        },
        /* ──── 8. Persona: Auditor (مدقق) ──── */
        {
            title: __("For Auditors"),
            icon: "clipboard-check",
            content: `
                <div class="caps-about-card">
                    <h3>📋 ${__("Auditor — Verification & Compliance Assurance")}</h3>
                    <p>${__("CAPS provides comprehensive audit infrastructure — verify access policies, review historical states, and generate compliance evidence without relying on manual logs.")}</p>
                    <div class="caps-stakeholder-grid">
                        <div class="caps-stakeholder-item">
                            <strong>${__("What you see")}</strong>
                            <ul>
                                <li>${__("CAPS Audit Log — every capability change timestamped and attributed")}</li>
                                <li>${__("Capability Snapshots — point-in-time access states for any date")}</li>
                                <li>${__("Capability Coverage Report — identify unused or over-assigned capabilities")}</li>
                                <li>${__("User Access Matrix — comprehensive user × capability cross-reference")}</li>
                                <li>${__("Compare Users tool — side-by-side permission diff for any two users")}</li>
                            </ul>
                        </div>
                        <div class="caps-stakeholder-item">
                            <strong>${__("What you verify")}</strong>
                            <ul>
                                <li>${__("Least-privilege compliance — no user has unnecessary access")}</li>
                                <li>${__("Separation of duties — conflicting capabilities not co-assigned")}</li>
                                <li>${__("Temporal access — time-boxed capabilities expired as scheduled")}</li>
                                <li>${__("Policy consistency — automated rules match written security policies")}</li>
                                <li>${__("Change history — all capability modifications fully traceable")}</li>
                            </ul>
                        </div>
                        <div class="caps-stakeholder-item">
                            <strong>${__("Audit workflows")}</strong>
                            <ul>
                                <li>${__("Periodic review: Compare current snapshot with previous for drift detection")}</li>
                                <li>${__("Incident response: Trace exact capabilities a user had at incident time")}</li>
                                <li>${__("Onboarding/Offboarding: Verify complete capability grant/revoke cycles")}</li>
                                <li>${__("External audit: Export Access Matrix and Audit Reports as evidence")}</li>
                            </ul>
                        </div>
                    </div>
                </div>`,
        },
        /* ──── 9. Competitor Comparison ──── */
        {
            title: __("Why CAPS? — Competitive Comparison"),
            icon: "vs",
            content: `
                <div class="caps-about-card">
                    <h3>⚖️ ${__("CAPS vs. Alternatives")}</h3>
                    <p>${__("See how CAPS compares to built-in Frappe permissions and enterprise access governance solutions.")}</p>
                    <div class="caps-compare-table-wrapper">
                        <table class="caps-compare-table">
                            <thead>
                                <tr>
                                    <th>${__("Feature")}</th>
                                    <th style="background:${BRAND_LIGHT};color:${BRAND_DARK}"><strong>CAPS</strong></th>
                                    <th>${__("Built-in Frappe Roles")}</th>
                                    <th>SAP GRC</th>
                                    <th>Oracle Access Gov.</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>${__("Atomic capabilities")}</td>
                                    <td class="caps-yes">✅ ${__("Full")}</td>
                                    <td class="caps-no">❌ ${__("Roles only")}</td>
                                    <td class="caps-partial">⚠️ ${__("Via GRC rules")}</td>
                                    <td class="caps-partial">⚠️ ${__("Limited")}</td>
                                </tr>
                                <tr>
                                    <td>${__("Field-level masking")}</td>
                                    <td class="caps-yes">✅ ${__("Per capability")}</td>
                                    <td class="caps-no">❌ ${__("None")}</td>
                                    <td class="caps-yes">✅</td>
                                    <td class="caps-yes">✅</td>
                                </tr>
                                <tr>
                                    <td>${__("Action-level gating")}</td>
                                    <td class="caps-yes">✅ ${__("Per button/workflow")}</td>
                                    <td class="caps-no">❌ ${__("DocType level")}</td>
                                    <td class="caps-partial">⚠️ ${__("Transaction level")}</td>
                                    <td class="caps-partial">⚠️</td>
                                </tr>
                                <tr>
                                    <td>${__("Policy automation")}</td>
                                    <td class="caps-yes">✅ ${__("Conditional rules")}</td>
                                    <td class="caps-no">❌</td>
                                    <td class="caps-yes">✅</td>
                                    <td class="caps-yes">✅</td>
                                </tr>
                                <tr>
                                    <td>${__("Time-boxed access")}</td>
                                    <td class="caps-yes">✅ ${__("Built-in")}</td>
                                    <td class="caps-no">❌</td>
                                    <td class="caps-yes">✅</td>
                                    <td class="caps-yes">✅</td>
                                </tr>
                                <tr>
                                    <td>${__("Audit trail")}</td>
                                    <td class="caps-yes">✅ ${__("Complete")}</td>
                                    <td class="caps-partial">⚠️ ${__("Activity Log only")}</td>
                                    <td class="caps-yes">✅</td>
                                    <td class="caps-yes">✅</td>
                                </tr>
                                <tr>
                                    <td>${__("Compliance snapshots")}</td>
                                    <td class="caps-yes">✅</td>
                                    <td class="caps-no">❌</td>
                                    <td class="caps-yes">✅</td>
                                    <td class="caps-yes">✅</td>
                                </tr>
                                <tr>
                                    <td>${__("Visual graph explorer")}</td>
                                    <td class="caps-yes">✅ ${__("Interactive")}</td>
                                    <td class="caps-no">❌</td>
                                    <td class="caps-no">❌</td>
                                    <td class="caps-partial">⚠️</td>
                                </tr>
                                <tr>
                                    <td>${__("Rate limiting")}</td>
                                    <td class="caps-yes">✅ ${__("Per capability")}</td>
                                    <td class="caps-no">❌</td>
                                    <td class="caps-no">❌</td>
                                    <td class="caps-no">❌</td>
                                </tr>
                                <tr>
                                    <td>${__("Frappe native")}</td>
                                    <td class="caps-yes">✅ ${__("100%")}</td>
                                    <td class="caps-yes">✅</td>
                                    <td class="caps-no">❌ ${__("SAP only")}</td>
                                    <td class="caps-no">❌ ${__("Oracle only")}</td>
                                </tr>
                                <tr>
                                    <td>${__("Cost")}</td>
                                    <td class="caps-yes">✅ ${__("Included")}</td>
                                    <td class="caps-yes">✅ ${__("Free")}</td>
                                    <td class="caps-no">💰 ${__("Enterprise license")}</td>
                                    <td class="caps-no">💰 ${__("Enterprise license")}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    <p class="mt-3 text-muted" style="font-size:.85rem;">${__("CAPS brings enterprise-grade access governance to the Frappe ecosystem — at a fraction of the cost of SAP GRC or Oracle Access Governance, with deep native integration.")}</p>
                </div>`,
        },
        /* ──── 10. Industry Use Cases ──── */
        {
            title: __("Industry Use Cases"),
            icon: "building-factory-2",
            content: `
                <div class="caps-about-card">
                    <h3>🏭 ${__("How CAPS Adapts to Your Industry")}</h3>
                    <p>${__("CAPS is domain-agnostic — it provides the access governance layer that adapts to any industry's compliance requirements.")}</p>
                    <div class="caps-industry-grid">
                        <div class="caps-industry-card" style="border-top:3px solid ${BRAND}">
                            <div class="caps-industry-icon">🏗️</div>
                            <strong>${__("Construction & Contracting")}</strong>
                            <ul>
                                <li>${__("Mask cost data from site engineers (Field Capability Map)")}</li>
                                <li>${__("Gate project approval actions by project value threshold")}</li>
                                <li>${__("Department-based groups for regional offices")}</li>
                            </ul>
                        </div>
                        <div class="caps-industry-card" style="border-top:3px solid #3B82F6">
                            <div class="caps-industry-icon">🏥</div>
                            <strong>${__("Healthcare")}</strong>
                            <ul>
                                <li>${__("HIPAA-aligned field masking for patient PII")}</li>
                                <li>${__("Role-based access to medical records vs. billing")}</li>
                                <li>${__("Time-boxed access for visiting consultants")}</li>
                            </ul>
                        </div>
                        <div class="caps-industry-card" style="border-top:3px solid #8B5CF6">
                            <div class="caps-industry-icon">🏦</div>
                            <strong>${__("Financial Services")}</strong>
                            <ul>
                                <li>${__("Separation of duties — prevent same user from creating and approving")}</li>
                                <li>${__("Rate limiting on high-value transaction approvals")}</li>
                                <li>${__("Periodic compliance snapshots for regulatory audits")}</li>
                            </ul>
                        </div>
                        <div class="caps-industry-card" style="border-top:3px solid #F59E0B">
                            <div class="caps-industry-icon">🎓</div>
                            <strong>${__("Education")}</strong>
                            <ul>
                                <li>${__("Student data privacy — restrict grade/record access by department")}</li>
                                <li>${__("Exam management — time-boxed access during exam periods")}</li>
                                <li>${__("Multi-campus site profiles with separate capability sets")}</li>
                            </ul>
                        </div>
                        <div class="caps-industry-card" style="border-top:3px solid #EF4444">
                            <div class="caps-industry-icon">🛒</div>
                            <strong>${__("Retail & E-Commerce")}</strong>
                            <ul>
                                <li>${__("Mask pricing/margin data from sales floor staff")}</li>
                                <li>${__("Gate discount approval actions by amount threshold")}</li>
                                <li>${__("Regional groups for franchise/branch management")}</li>
                            </ul>
                        </div>
                        <div class="caps-industry-card" style="border-top:3px solid #06B6D4">
                            <div class="caps-industry-icon">⚙️</div>
                            <strong>${__("Manufacturing")}</strong>
                            <ul>
                                <li>${__("BOM cost protection — restrict access to production costs")}</li>
                                <li>${__("Quality control gates — restrict QC approval to certified users")}</li>
                                <li>${__("Shift-based time-boxed access for production supervisors")}</li>
                            </ul>
                        </div>
                    </div>
                </div>`,
        },
        /* ──── 11. Integration Map ──── */
        {
            title: __("Integration Map"),
            icon: "plug-connected",
            content: `
                <div class="caps-about-card">
                    <h3>🔌 ${__("Deep Ecosystem Integration")}</h3>
                    <p>${__("CAPS integrates natively with the Frappe/ERPNext ecosystem — no middleware, no external dependencies.")}</p>
                    <div class="caps-integration-grid">
                        <div class="caps-integration-item" style="border-left:4px solid ${BRAND}">
                            <strong>Frappe Core</strong>
                            <p>${__("Boot session injection · doc_events hooks · Real-time cache invalidation · Permission query builder override")}</p>
                        </div>
                        <div class="caps-integration-item" style="border-left:4px solid #3B82F6">
                            <strong>ERPNext</strong>
                            <p>${__("Field-level cost/margin masking · Action restrictions on Sales/Purchase transactions · Workflow gate integration")}</p>
                        </div>
                        <div class="caps-integration-item" style="border-left:4px solid #8B5CF6">
                            <strong>HRMS</strong>
                            <p>${__("Employee-linked capability assignment · Department/designation-based groups · Salary field masking")}</p>
                        </div>
                        <div class="caps-integration-item" style="border-left:4px solid #F59E0B">
                            <strong>frappe_visual</strong>
                            <p>${__("App Map · ERD · Dependency Graph · Storyboard · Floating Window · Icon System")}</p>
                        </div>
                        <div class="caps-integration-item" style="border-left:4px solid #06B6D4">
                            <strong>${__("Third-Party Apps")}</strong>
                            <p>${__("Any Frappe app can declare caps_capabilities and caps_field_maps in hooks.py for instant CAPS integration.")}</p>
                        </div>
                    </div>
                </div>`,
        },
        /* ──── 12. Security & Reports ──── */
        {
            title: __("Security & Compliance Reports"),
            icon: "report-analytics",
            content: `
                <div class="caps-about-card">
                    <h3>📊 ${__("Enterprise Audit & Compliance Infrastructure")}</h3>
                    <div class="caps-reports-grid">
                        <div class="caps-report-card">
                            <div class="caps-report-icon">📈</div>
                            <strong>${__("Capability Coverage")}</strong>
                            <p>${__("Identify gaps — which capabilities are assigned, which are unused, which users lack coverage.")}</p>
                        </div>
                        <div class="caps-report-card">
                            <div class="caps-report-icon">🔲</div>
                            <strong>${__("User Access Matrix")}</strong>
                            <p>${__("Cross-reference users × capabilities. Filter by role, department, or bundle. Export for external audits.")}</p>
                        </div>
                        <div class="caps-report-card">
                            <div class="caps-report-icon">📝</div>
                            <strong>${__("CAPS Audit Report")}</strong>
                            <p>${__("Complete trail — every grant, revocation, policy trigger, and escalation with timestamps and actors.")}</p>
                        </div>
                        <div class="caps-report-card">
                            <div class="caps-report-icon">📸</div>
                            <strong>${__("Capability Snapshots")}</strong>
                            <p>${__("Point-in-time freeze of all user capabilities. Compare snapshots to detect drift over time.")}</p>
                        </div>
                    </div>
                    <div class="mt-3">
                        <h4>${__("Security Enforcement")}</h4>
                        <ul>
                            <li>${__("Rate limiting per capability — prevent abuse of sensitive operations")}</li>
                            <li>${__("Time-boxed capabilities — automatic expiry with no manual cleanup")}</li>
                            <li>${__("Policy engine — conditional rules auto-grant/revoke based on context")}</li>
                            <li>${__("Real-time cache invalidation — permission changes take effect instantly")}</li>
                            <li>${__("Login audit integration — correlate access events with session data")}</li>
                        </ul>
                    </div>
                </div>`,
        },
        /* ──── 13. Per-App CAPS Integration ──── */
        {
            title: __("Per-App CAPS Integration"),
            icon: "code",
            content: `
                <div class="caps-about-card">
                    <h3>🧩 ${__("How Apps Integrate with CAPS")}</h3>
                    <p>${__("Any Frappe app can declare its capabilities in hooks.py — CAPS auto-discovers and enforces them.")}</p>
                    <pre style="background:var(--bg-color);border:1px solid var(--border-color);border-radius:var(--border-radius);padding:1rem;overflow-x:auto;font-size:.82rem;line-height:1.6"><code><span style="color:var(--text-muted)"># In your app's hooks.py</span>
caps_capabilities = [
    {"name": "VX_view_dashboard",  "category": "Module"},
    {"name": "VX_approve_orders",  "category": "Action"},
    {"name": "VX_view_cost_data",  "category": "Field"},
    {"name": "VX_export_reports",  "category": "Report"},
]

caps_field_maps = [
    {
        "capability": "VX_view_cost_data",
        "doctype": "Project",
        "field": "total_cost",
        "behavior": "mask",
    },
]</code></pre>
                    <p class="mt-3 text-muted" style="font-size:.85rem;">${__("CAPS discovers capabilities from all installed apps at boot time. No code changes needed in the CAPS app itself.")}</p>
                </div>`,
        },
        /* ──── 14. Getting Started ──── */
        {
            title: __("Getting Started"),
            icon: "rocket",
            content: `
                <div class="caps-about-card">
                    <h3>🚀 ${__("Quick Start Guide")}</h3>
                    <div class="caps-steps">
                        <div class="caps-step">
                            <div class="caps-step-num" style="background:${BRAND}">1</div>
                            <div>
                                <strong>${__("Define Capabilities")}</strong>
                                <p>${__("Create atomic capabilities like 'View Cost Data', 'Approve Invoice', 'Export Report'.")}</p>
                            </div>
                        </div>
                        <div class="caps-step">
                            <div class="caps-step-num" style="background:${BRAND}">2</div>
                            <div>
                                <strong>${__("Build Bundles & Map Roles")}</strong>
                                <p>${__("Group related capabilities into reusable bundles. Map Frappe roles to CAPS capabilities.")}</p>
                            </div>
                        </div>
                        <div class="caps-step">
                            <div class="caps-step-num" style="background:${BRAND}">3</div>
                            <div>
                                <strong>${__("Assign to Users & Groups")}</strong>
                                <p>${__("Grant capabilities directly or through Permission Groups for team-based assignment.")}</p>
                            </div>
                        </div>
                        <div class="caps-step">
                            <div class="caps-step-num" style="background:${BRAND}">4</div>
                            <div>
                                <strong>${__("Configure Restrictions")}</strong>
                                <p>${__("Set up Field Capability Maps (mask sensitive data) and Action Capability Maps (gate workflows).")}</p>
                            </div>
                        </div>
                        <div class="caps-step">
                            <div class="caps-step-num" style="background:${BRAND}">5</div>
                            <div>
                                <strong>${__("Enable Policies & Monitoring")}</strong>
                                <p>${__("Create automated policies, set rate limits, schedule compliance snapshots, and review audit logs.")}</p>
                            </div>
                        </div>
                    </div>
                    <div class="mt-4 text-center">
                        <button class="btn btn-primary btn-lg" onclick="frappe.set_route('caps-admin')" style="background:${BRAND};border-color:${BRAND}">
                            ${__("Go to CAPS Admin")} →
                        </button>
                        <button class="btn btn-default btn-lg ml-2" onclick="frappe.set_route('caps-onboarding')">
                            ${__("Start Onboarding")} →
                        </button>
                    </div>
                </div>`,
        },
    ];

    /* ──── Build storyboard ──── */
    const container = $(page.body).find("#caps-about-root");
    if (!container.length) return;

    if (frappe.visual && frappe.visual.storyboard) {
        frappe.visual.storyboard({
            container: container,
            slides: slides,
            brandColor: BRAND,
            showNavTop: true,
            showNavBottom: true,
            onSlideChange(idx) {
                if (slides[idx] && slides[idx].onShow) {
                    setTimeout(() => slides[idx].onShow(), 300);
                }
            },
        });
    } else {
        // Fallback: render slides as cards
        render_fallback(container, slides, BRAND);
    }
}

/* ══════════════════════════════════════════════════════════════ */
/*  Fallback renderer (no frappe_visual)                        */
/* ══════════════════════════════════════════════════════════════ */
function render_fallback(container, slides, brand) {
    let current = 0;

    function render(idx) {
        const s = slides[idx];
        container.html(`
            <style>
                .caps-about-card{background:var(--card-bg);border-radius:var(--border-radius-lg);padding:2rem;margin:1rem 0;box-shadow:var(--shadow-sm)}
                .caps-about-hero{text-align:center;margin-bottom:1.5rem}
                .caps-about-features{display:flex;flex-wrap:wrap;gap:.5rem;margin-top:1rem}
                .caps-feature-chip{background:${brand}15;color:${brand};padding:.4rem .8rem;border-radius:2rem;font-size:.85rem;display:flex;align-items:center;gap:.3rem}
                .caps-stakeholder-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:1.5rem;margin-top:1rem}
                @media(max-width:768px){.caps-stakeholder-grid{grid-template-columns:1fr}}
                .caps-stakeholder-item{background:var(--bg-color);padding:1rem;border-radius:var(--border-radius)}
                .caps-stakeholder-item ul{margin-top:.5rem;padding-left:1.2rem}
                .caps-integration-grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-top:1rem}
                .caps-integration-item{padding:1rem;background:var(--bg-color);border-radius:var(--border-radius)}
                .caps-integration-item p{margin:.3rem 0 0;font-size:.85rem;color:var(--text-muted)}
                .caps-reports-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;margin-top:1rem}
                .caps-report-card{text-align:center;padding:1.2rem;background:var(--bg-color);border-radius:var(--border-radius)}
                .caps-report-icon{font-size:2rem;margin-bottom:.5rem}
                .caps-report-card p{font-size:.8rem;color:var(--text-muted);margin-top:.3rem}
                .caps-steps{display:flex;flex-direction:column;gap:1rem;margin-top:1rem}
                .caps-step{display:flex;align-items:flex-start;gap:1rem}
                .caps-step-num{width:36px;height:36px;border-radius:50%;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:bold;flex-shrink:0}
                .caps-step p{margin:.2rem 0 0;font-size:.85rem;color:var(--text-muted)}
                .caps-nav-bar{display:flex;justify-content:space-between;align-items:center;padding:.8rem 0}
                .caps-nav-bar .btn{min-width:100px}
                .caps-slide-counter{font-size:.85rem;color:var(--text-muted)}
                .caps-compare-table-wrapper{overflow-x:auto;margin-top:1rem}
                .caps-compare-table{width:100%;border-collapse:collapse;font-size:.85rem}
                .caps-compare-table th,.caps-compare-table td{padding:.6rem .8rem;border:1px solid var(--border-color);text-align:center}
                .caps-compare-table th{background:var(--bg-color);font-weight:600;white-space:nowrap}
                .caps-compare-table td:first-child{text-align:left;font-weight:500}
                .caps-yes{background:#D1FAE520;color:#065F46}
                .caps-partial{background:#FEF3C720;color:#92400E}
                .caps-no{background:#FEE2E220;color:#991B1B}
                .caps-industry-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1rem;margin-top:1rem}
                .caps-industry-card{background:var(--bg-color);padding:1.2rem;border-radius:var(--border-radius)}
                .caps-industry-card ul{padding-left:1.2rem;margin-top:.5rem;font-size:.85rem}
                .caps-industry-icon{font-size:1.8rem;margin-bottom:.5rem}
            </style>
            <div class="caps-nav-bar">
                <button class="btn btn-default btn-sm" ${idx === 0 ? "disabled" : ""} onclick="window._capsAboutNav(${idx - 1})">← ${__("Previous")}</button>
                <span class="caps-slide-counter">${idx + 1} / ${slides.length}</span>
                <button class="btn btn-primary btn-sm" ${idx === slides.length - 1 ? "disabled" : ""} onclick="window._capsAboutNav(${idx + 1})" style="background:${brand};border-color:${brand}">
                    ${__("Next")} →
                </button>
            </div>
            <h2 style="text-align:center;margin:1rem 0">${s.title}</h2>
            ${typeof s.content === "function" ? "" : s.content}
            <div class="caps-nav-bar">
                <button class="btn btn-default btn-sm" ${idx === 0 ? "disabled" : ""} onclick="window._capsAboutNav(${idx - 1})">← ${__("Previous")}</button>
                <span class="caps-slide-counter">${idx + 1} / ${slides.length}</span>
                <button class="btn btn-primary btn-sm" ${idx === slides.length - 1 ? "disabled" : ""} onclick="window._capsAboutNav(${idx + 1})" style="background:${brand};border-color:${brand}">
                    ${__("Next")} →
                </button>
            </div>
        `);
        if (s.onShow) setTimeout(() => s.onShow(), 300);
    }

    window._capsAboutNav = function (idx) {
        if (idx >= 0 && idx < slides.length) {
            current = idx;
            render(current);
        }
    };

    render(0);
}
