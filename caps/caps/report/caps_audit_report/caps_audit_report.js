// Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
// Developer Website: https://arkan.it.com
// License: MIT
// For license information, please see license.txt

frappe.query_reports["CAPS Audit Report"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "user",
			label: __("User"),
			fieldtype: "Link",
			options: "User",
		},
		{
			fieldname: "action",
			label: __("Action"),
			fieldtype: "Select",
			options: "\ncapability_check\ncapability_grant\ncapability_revoke\nbulk_grant\nbulk_revoke\npolicy_applied\npolicy_expired\ndelegation\nimpersonation\ntransfer",
		},
		{
			fieldname: "capability",
			label: __("Capability"),
			fieldtype: "Link",
			options: "Capability",
		},
		{
			fieldname: "result",
			label: __("Result"),
			fieldtype: "Select",
			options: "\ngranted\ndenied\nsuccess\nfailed",
		},
	],
};
