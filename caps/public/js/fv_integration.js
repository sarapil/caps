// Copyright (c) 2024, Arkan Lab — https://arkan.it.com
// License: MIT
// frappe_visual Integration for CAPS

(function() {
    "use strict";

    // App branding registration
    const APP_CONFIG = {
        name: "caps",
        title: __("CAPS"),
        color: "#059669",
        module: "CAPS",
    };

    // Initialize visual enhancements when ready
    $(document).on("app_ready", function() {
        // Register app color with visual theme system
        if (frappe.visual && frappe.visual.ThemeManager) {
            try {
                document.documentElement.style.setProperty(
                    "--caps-primary",
                    APP_CONFIG.color
                );
            } catch(e) {}
        }

        // Initialize bilingual tooltips for Arabic support
        if (frappe.visual && frappe.visual.bilingualTooltip) {
            // bilingualTooltip auto-initializes — just ensure it's active
        }
    });

    // Route-based visual page rendering
    $(document).on("page-change", function() {
        if (!frappe.visual || !frappe.visual.generator) return;

    // Visual Settings Page
    if (frappe.get_route_str() === 'caps-settings') {
        const page = frappe.container.page;
        if (page && page.main && frappe.visual.generator) {
            frappe.visual.generator.settingsPage(
                page.main[0] || page.main,
                "CAPS Settings"
            );
        }
    }

    // Visual Reports Hub
    if (frappe.get_route_str() === 'caps-reports') {
        const page = frappe.container.page;
        if (page && page.main && frappe.visual.generator) {
            frappe.visual.generator.reportsHub(
                page.main[0] || page.main,
                "CAPS"
            );
        }
    }
    });
})();
