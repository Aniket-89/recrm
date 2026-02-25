// Copyright (c) 2026, Real Estate CRM and contributors
// For license information, please see license.txt

frappe.query_reports["Booking Register"] = {
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
			fieldname: "booking_status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nDraft\nBooked\nPayment In Progress\nPossession Due\nCompleted\nCancelled",
		},
	],
};
