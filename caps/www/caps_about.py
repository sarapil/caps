# Copyright (c) 2024, Arkan Lab and contributors
# For license information, please see license.txt

import frappe


def get_context(context):
    context.no_cache = 1
    context.title = frappe._("About CAPS")
    context.parents = [{"name": frappe._("Home"), "route": "/"}]
