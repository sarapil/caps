// Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
// Developer Website: https://arkan.it.com
// License: MIT
// For license information, please see license.txt

/**
 * CAPS — Client-Side Controller
 * ===============================
 *
 * Provides `frappe.caps` global object for capability-based UI enforcement.
 *
 * Auto-enforces field + action restrictions on every form refresh.
 * Data is bootstrapped from boot_session and cached client-side.
 *
 * Usage:
 *   frappe.caps.has("field:Customer:phone")  → Promise<boolean>
 *   frappe.caps.enforce(frm)                 → auto-called on form events
 */

(function () {
    "use strict";

    // ── Client-side cache ─────────────────────────────────────────
    let _capabilities = null;
    let _fieldRestrictions = null;
    let _actionRestrictions = null;
    let _version = 0;
    let _cacheTS = 0;
    const _CACHE_TTL = 60000; // 60 seconds

    // ── Initialise from boot ──────────────────────────────────────
    function _initFromBoot() {
        const boot = frappe.boot || {};
        const caps = boot.caps || {};
        _capabilities = new Set(caps.capabilities || []);
        _fieldRestrictions = caps.field_restrictions || {};
        _actionRestrictions = caps.action_restrictions || {};
        _version = caps.version || 0;
        _cacheTS = Date.now();
    }

    // ── Ensure cache is fresh ─────────────────────────────────────
    async function _ensureCache() {
        if (_capabilities && (Date.now() - _cacheTS < _CACHE_TTL)) {
            return;
        }
        // Refresh from server
        try {
            const r = await frappe.xcall("caps.api.get_all_restrictions");
            if (r) {
                _fieldRestrictions = r.field_restrictions || {};
                _actionRestrictions = r.action_restrictions || {};
                _version = r.version || 0;
                _cacheTS = Date.now();
            }
        } catch (e) {
            console.warn("[CAPS] Cache refresh failed:", e);
        }
    }

    // ── Public API ────────────────────────────────────────────────

    frappe.caps = {
        /**
         * Auto-enforce field + action restrictions on a form.
         * Called automatically on form refresh via the hook below.
         */
        async enforce(frm) {
            if (!frm || !frm.doctype) return;
            await _ensureCache();

            const dt = frm.doctype;

            // ── Field restrictions ──────────────────────────
            const fieldRules = _fieldRestrictions[dt] || {};
            for (const [fieldname, rule] of Object.entries(fieldRules)) {
                const field = frm.fields_dict[fieldname];
                if (!field) continue;

                switch (rule.behavior) {
                    case "hide":
                        frm.set_df_property(fieldname, "hidden", 1);
                        break;
                    case "read_only":
                        frm.set_df_property(fieldname, "read_only", 1);
                        break;
                    case "mask":
                        frm.set_df_property(fieldname, "read_only", 1);
                        if (frm.doc[fieldname]) {
                            const masked = _applyMask(
                                String(frm.doc[fieldname]),
                                rule.mask_pattern
                            );
                            // Show masked value without changing actual doc
                            $(field.$input || field.$wrapper.find(".like-disabled-input"))
                                .val(masked)
                                .text(masked);
                        }
                        break;
                    case "custom":
                        if (rule.custom_handler) {
                            try {
                                // eslint-disable-next-line no-eval
                                eval(rule.custom_handler);
                            } catch (e) {
                                console.warn(`[CAPS] Custom handler error for ${fieldname}:`, e);
                            }
                        }
                        break;
                }
            }

            // ── Action restrictions ─────────────────────────
            const actionRules = _actionRestrictions[dt] || [];
            for (const rule of actionRules) {
                _enforceAction(frm, rule);
            }
        },

        /**
         * Check if current user has a capability.
         */
        async has(capability) {
            if (!_capabilities) _initFromBoot();
            return _capabilities.has(capability);
        },

        /**
         * Check if current user has ANY of the capabilities.
         */
        async hasAny(...capabilities) {
            if (!_capabilities) _initFromBoot();
            return capabilities.some((c) => _capabilities.has(c));
        },

        /**
         * Check if current user has ALL capabilities.
         */
        async hasAll(...capabilities) {
            if (!_capabilities) _initFromBoot();
            return capabilities.every((c) => _capabilities.has(c));
        },

        /**
         * Get restrictions for a specific doctype.
         */
        async getRestrictions(doctype) {
            await _ensureCache();
            return {
                fields: _fieldRestrictions[doctype] || {},
                actions: _actionRestrictions[doctype] || [],
            };
        },

        /**
         * Conditional execution: run callback only if user has capability.
         */
        async ifCan(capability, callback) {
            const can = await this.has(capability);
            if (can && typeof callback === "function") {
                callback();
            }
            return can;
        },

        /**
         * Force-refresh cache from server.
         */
        async bustCache() {
            _capabilities = null;
            _fieldRestrictions = null;
            _actionRestrictions = null;
            _cacheTS = 0;
            try {
                await frappe.xcall("caps.api.bust_cache");
                const r = await frappe.xcall("caps.api.get_all_restrictions");
                if (r) {
                    _fieldRestrictions = r.field_restrictions || {};
                    _actionRestrictions = r.action_restrictions || {};
                    _version = r.version || 0;
                }
                const caps = await frappe.xcall("caps.api.get_my_capabilities");
                if (caps) {
                    _capabilities = new Set(caps);
                }
                _cacheTS = Date.now();
            } catch (e) {
                console.warn("[CAPS] Cache bust failed:", e);
            }
        },

        /**
         * Get current map version (for staleness checks).
         */
        getVersion() {
            return _version;
        },
    };

    // ── Action enforcement helper ─────────────────────────────────

    function _enforceAction(frm, rule) {
        const { action_id, action_type, fallback_behavior, fallback_message } = rule;

        if (action_type === "button" || action_type === "menu_item") {
            // Find and hide/disable the button
            const $btns = frm.$wrapper
                ? frm.$wrapper.find(
                    `.btn-primary-dark:contains("${action_id}"), ` +
                    `.btn-default:contains("${action_id}"), ` +
                    `.dropdown-item:contains("${action_id}")`
                )
                : $();

            if (fallback_behavior === "hide") {
                $btns.closest(".btn, .dropdown-item, li").hide();
            } else if (fallback_behavior === "disable") {
                $btns.prop("disabled", true).addClass("disabled");
                if (fallback_message) {
                    $btns.attr("title", fallback_message);
                }
            }
        }

        if (action_type === "workflow_action") {
            // Hide workflow action buttons
            const $wfBtns = frm.$wrapper
                ? frm.$wrapper.find(
                    `.btn-primary[data-action="${action_id}"], ` +
                    `.workflow-button-area .btn:contains("${action_id}")`
                )
                : $();

            if (fallback_behavior === "hide") {
                $wfBtns.hide();
            } else if (fallback_behavior === "disable") {
                $wfBtns.prop("disabled", true);
                if (fallback_message) {
                    $wfBtns.attr("title", fallback_message);
                }
            }
        }

        if (action_type === "print_format") {
            // Hide print format from the menu
            frm.$wrapper &&
                frm.$wrapper
                    .find(`.dropdown-item:contains("${action_id}")`)
                    .hide();
        }
    }

    // ── Mask helper ───────────────────────────────────────────────

    function _applyMask(value, pattern) {
        if (!pattern) {
            return "●".repeat(Math.min(value.length, 8));
        }
        let result = pattern;

        // {last4} → last N chars
        const lastMatch = pattern.match(/\{last(\d+)\}/);
        if (lastMatch) {
            const n = parseInt(lastMatch[1]);
            result = result.replace(
                lastMatch[0],
                value.length >= n ? value.slice(-n) : value
            );
        }

        // {first2} → first N chars
        const firstMatch = pattern.match(/\{first(\d+)\}/);
        if (firstMatch) {
            const n = parseInt(firstMatch[1]);
            result = result.replace(
                firstMatch[0],
                value.length >= n ? value.slice(0, n) : value
            );
        }

        return result;
    }

    // ── Auto-Enforce on Form Events ──────────────────────────────

    // Initialise capabilities from boot data
    $(document).ready(function () {
        _initFromBoot();
        _showImpersonationBanner();
    });

    // ── Impersonation Banner ─────────────────────────────────────

    function _showImpersonationBanner() {
        const boot = frappe.boot || {};
        const caps = boot.caps || {};
        const target = caps.impersonating;

        // Remove any existing banner first
        $(".caps-impersonation-banner").remove();

        if (!target) return;

        const $banner = $(`
            <div class="caps-impersonation-banner"
                 style="position:fixed;top:0;left:0;right:0;z-index:10000;
                        background:#ff6b35;color:#fff;text-align:center;
                        padding:6px 12px;font-size:13px;font-weight:600;">
                <i class="fa fa-user-secret"></i>
                ${__("CAPS Impersonation Active")} — ${__("Viewing as")}
                <strong>${frappe.utils.escape_html(target)}</strong>
                <button class="btn btn-xs btn-light caps-stop-impersonation"
                        style="margin-left:12px;font-weight:600;">
                    ${__("Stop")}
                </button>
            </div>
        `);
        $banner.find(".caps-stop-impersonation").on("click", function () {
            frappe.call({
                method: "caps.api_impersonation.stop_impersonation",
                callback: function () {
                    $(".caps-impersonation-banner").remove();
                    frappe.show_alert({
                        message: __("Impersonation stopped"),
                        indicator: "green",
                    });
                    // Push body back down
                    $("body").css("margin-top", "");
                    // Reload to get real caps
                    location.reload();
                },
            });
        });
        $("body").prepend($banner);
        // Push body down so banner doesn't overlap navbar
        $("body").css("margin-top", "38px");
    }

    // Hook into every form refresh
    $(document).on("form-refresh", function (event, frm) {
        if (frm && frappe.caps) {
            frappe.caps.enforce(frm);
        }
    });

    // Also hook via frappe.ui.form.on for broader coverage
    if (frappe.ui && frappe.ui.form) {
        const _origTrigger = frappe.ui.form.trigger;
        if (_origTrigger) {
            frappe.ui.form.trigger = function (doctype, event, frm) {
                const result = _origTrigger.apply(this, arguments);
                if (event === "refresh" && frm && frappe.caps) {
                    frappe.caps.enforce(frm);
                }
                return result;
            };
        }
    }
})();
