// Copyright (c) 2024, Arkan Lab — https://arkan.it.com
// License: MIT
// frappe_visual Integration for CAPS — Scene Dashboard & Visual Components

(function() {
    "use strict";

    // ── App Configuration ─────────────────────────────────────────
    const APP_CONFIG = {
        name: "caps",
        title: "CAPS",
        color: "#10B981",
        gradient: "linear-gradient(135deg, #10B981, #059669)",
        module: "CAPS",
    };

    // ── CSS Variables Registration ────────────────────────────────
    function registerCSSVariables() {
        document.documentElement.style.setProperty("--caps-primary", APP_CONFIG.color);
        document.documentElement.style.setProperty("--caps-gradient", APP_CONFIG.gradient);
    }

    // ── Scene Dashboard Builder ───────────────────────────────────
    async function buildSceneDashboard(container) {
        if (!frappe.visual) {
            console.warn("[CAPS] frappe_visual not available for scene dashboard");
            return null;
        }

        try {
            // Create scene container if not exists
            let sceneContainer = container.querySelector('#caps-scene-header');
            if (!sceneContainer) {
                sceneContainer = document.createElement('div');
                sceneContainer.id = 'caps-scene-header';
                sceneContainer.className = 'caps-scene-container fv-fx-glass';
                container.insertBefore(sceneContainer, container.firstChild);
            }

            // Initialize scene with office preset
            const scene = await frappe.visual.scenePresetOffice({
                container: '#caps-scene-header',
                theme: 'cool',
                frames: [
                    { label: __('Active Capabilities'), status: 'success' },
                    { label: __('Users with Access'), status: 'info' },
                    { label: __('Pending Requests'), status: 'warning' },
                    { label: __('Active Policies'), status: 'info' }
                ],
                documents: [
                    { 
                        label: __('Recent Audit Logs'),
                        href: '/app/caps-audit-log',
                        color: '#6366f1'
                    }
                ],
                books: [
                    { label: __('CAPS Help'), href: '/caps-onboarding', color: '#10B981' }
                ]
            });

            // Bind live data
            if (frappe.visual.sceneDataBinder) {
                await frappe.visual.sceneDataBinder({
                    engine: scene,
                    frames: [
                        {
                            label: __('Active Capabilities'),
                            doctype: 'Capability',
                            aggregate: 'count',
                            filters: { is_active: 1 },
                            status_rules: { '>50': 'success', '<10': 'warning' }
                        },
                        {
                            label: __('Users with Access'),
                            doctype: 'User Capability',
                            aggregate: 'count_distinct',
                            field: 'user',
                            status_rules: { '>100': 'success' }
                        },
                        {
                            label: __('Pending Requests'),
                            doctype: 'Capability Request',
                            aggregate: 'count',
                            filters: { status: 'Pending' },
                            status_rules: { '>0': 'warning', '>5': 'danger' }
                        },
                        {
                            label: __('Active Policies'),
                            doctype: 'Capability Policy',
                            aggregate: 'count',
                            filters: { is_enabled: 1 },
                            status_rules: {}
                        }
                    ],
                    refreshInterval: 30000
                });
            }

            return scene;
        } catch (e) {
            console.error("[CAPS] Scene dashboard error:", e);
            return null;
        }
    }

    // ── KPI Cards Builder (Fallback) ──────────────────────────────
    async function buildKPICards(container) {
        const kpiContainer = document.createElement('div');
        kpiContainer.className = 'caps-kpi-grid';
        kpiContainer.innerHTML = `
            <div class="caps-kpi-card fv-fx-glass fv-fx-hover-lift" data-stat="capabilities">
                <div class="caps-kpi-icon">🛡️</div>
                <div class="caps-kpi-value" data-field="capabilities_count">--</div>
                <div class="caps-kpi-label">${__('Active Capabilities')}</div>
            </div>
            <div class="caps-kpi-card fv-fx-glass fv-fx-hover-lift" data-stat="users">
                <div class="caps-kpi-icon">👥</div>
                <div class="caps-kpi-value" data-field="users_count">--</div>
                <div class="caps-kpi-label">${__('Users with Access')}</div>
            </div>
            <div class="caps-kpi-card fv-fx-glass fv-fx-hover-lift" data-stat="requests">
                <div class="caps-kpi-icon">📋</div>
                <div class="caps-kpi-value" data-field="pending_count">--</div>
                <div class="caps-kpi-label">${__('Pending Requests')}</div>
            </div>
            <div class="caps-kpi-card fv-fx-glass fv-fx-hover-lift" data-stat="policies">
                <div class="caps-kpi-icon">📜</div>
                <div class="caps-kpi-value" data-field="policies_count">--</div>
                <div class="caps-kpi-label">${__('Active Policies')}</div>
            </div>
        `;
        container.insertBefore(kpiContainer, container.firstChild);

        // Fetch and populate stats
        try {
            const stats = await frappe.xcall('caps.api_dashboard.get_dashboard_stats');
            if (stats) {
                animateNumber(kpiContainer.querySelector('[data-field="capabilities_count"]'), stats.capabilities_count || 0);
                animateNumber(kpiContainer.querySelector('[data-field="users_count"]'), stats.users_count || 0);
                animateNumber(kpiContainer.querySelector('[data-field="pending_count"]'), stats.pending_count || 0);
                animateNumber(kpiContainer.querySelector('[data-field="policies_count"]'), stats.policies_count || 0);
            }
        } catch (e) {
            console.warn("[CAPS] KPI fetch failed:", e);
        }
    }

    // ── Number Animation (GSAP-like) ──────────────────────────────
    function animateNumber(element, targetValue) {
        if (!element) return;
        const duration = 1000;
        const start = 0;
        const startTime = performance.now();
        
        function update(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
            const current = Math.round(start + (targetValue - start) * eased);
            element.textContent = current.toLocaleString();
            
            if (progress < 1) {
                requestAnimationFrame(update);
            }
        }
        requestAnimationFrame(update);
    }

    // ── Workspace Enhancement ─────────────────────────────────────
    async function enhanceWorkspace() {
        const workspaceMain = document.querySelector('.workspace-main');
        if (!workspaceMain) return;

        // Add visual effects classes
        workspaceMain.classList.add('fv-fx-page-enter');

        // Build scene dashboard or fallback KPI cards
        if (frappe.visual && frappe.visual.scenePresetOffice) {
            await buildSceneDashboard(workspaceMain);
        } else {
            await buildKPICards(workspaceMain);
        }
    }

    // ── Form Dashboard Enhancement ────────────────────────────────
    function enhanceFormDashboard(frm) {
        if (!frm || !frappe.visual) return;

        const capsDocTypes = [
            'Capability', 'Capability Bundle', 'User Capability',
            'Permission Group', 'Capability Policy', 'Capability Request'
        ];

        if (!capsDocTypes.includes(frm.doctype)) return;

        // Add visual form dashboard if available
        if (frappe.visual.formDashboard) {
            const dashContainer = frm.page.main.find('.form-dashboard');
            if (dashContainer.length) {
                frappe.visual.formDashboard(dashContainer[0], {
                    doctype: frm.doctype,
                    docname: frm.doc.name
                });
            }
        }
    }

    // ── Initialize ────────────────────────────────────────────────
    $(document).on("app_ready", function() {
        registerCSSVariables();

        // Initialize bilingual tooltips
        if (frappe.visual && frappe.visual.bilingualTooltip) {
            // Auto-initialized
        }
    });

    // Route-based enhancements
    $(document).on("page-change", function() {
        const route = frappe.get_route_str();

        // CAPS Admin workspace
        if (route === 'Workspaces/CAPS Admin' || route.includes('caps-admin')) {
            setTimeout(enhanceWorkspace, 100);
        }

        // Visual Settings Page
        if (route === 'caps-settings' && frappe.visual && frappe.visual.generator) {
            const page = frappe.container.page;
            if (page && page.main) {
                frappe.visual.generator.settingsPage(
                    page.main[0] || page.main,
                    "CAPS Settings"
                );
            }
        }

        // Visual Reports Hub
        if (route === 'caps-reports' && frappe.visual && frappe.visual.generator) {
            const page = frappe.container.page;
            if (page && page.main) {
                frappe.visual.generator.reportsHub(
                    page.main[0] || page.main,
                    "CAPS"
                );
            }
        }
    });

    // Form enhancements
    $(document).on("form-refresh", function(e, frm) {
        enhanceFormDashboard(frm);
    });

    // ── Export for external use ───────────────────────────────────
    frappe.caps = frappe.caps || {};
    frappe.caps.visual = {
        buildSceneDashboard,
        buildKPICards,
        animateNumber
    };
})();
