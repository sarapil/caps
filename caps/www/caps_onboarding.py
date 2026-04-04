# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

import frappe


def get_context(context):
    context.no_cache = 1
    context.title = frappe._("CAPS Onboarding")
    context.parents = [{"name": frappe._("Home"), "route": "/"}]
