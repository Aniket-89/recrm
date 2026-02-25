// Copyright (c) 2026, Real Estate CRM and contributors
// For license information, please see license.txt

frappe.query_reports["Payment Collection Report"] = {
	filters: [
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "Link",
			options: "RE Project",
		},
		{
			fieldname: "assigned_rm",
			label: __("RM"),
			fieldtype: "Link",
			options: "RE Relationship Manager",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "overdue_only",
			label: __("Overdue Only"),
			fieldtype: "Check",
			default: 0,
		},
	],
};
