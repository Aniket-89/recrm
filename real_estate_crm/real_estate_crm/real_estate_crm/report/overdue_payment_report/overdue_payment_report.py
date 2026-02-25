# Copyright (c) 2026, Real Estate CRM and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, getdate, date_diff


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"fieldname": "rm_name",
			"label": "RM Name",
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"fieldname": "booking_no",
			"label": "Booking No",
			"fieldtype": "Link",
			"options": "RE Booking",
			"width": 160,
		},
		{
			"fieldname": "customer",
			"label": "Customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 160,
		},
		{
			"fieldname": "plot",
			"label": "Plot",
			"fieldtype": "Link",
			"options": "RE Plot",
			"width": 120,
		},
		{
			"fieldname": "project",
			"label": "Project",
			"fieldtype": "Link",
			"options": "RE Project",
			"width": 140,
		},
		{
			"fieldname": "stage_name",
			"label": "Stage Name",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"fieldname": "amount_due",
			"label": "Amount Due",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"fieldname": "amount_received",
			"label": "Amount Received",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"fieldname": "balance",
			"label": "Balance",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"fieldname": "due_date",
			"label": "Due Date",
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"fieldname": "days_overdue",
			"label": "Days Overdue",
			"fieldtype": "Int",
			"width": 120,
		},
	]


def get_data(filters):
	conditions = ""
	if filters and filters.get("project"):
		conditions += " AND b.project = %(project)s"
	if filters and filters.get("rm"):
		conditions += " AND b.assigned_rm = %(rm)s"

	today = getdate()

	data = frappe.db.sql(
		"""
		SELECT
			rm.rm_name AS rm_name,
			b.name AS booking_no,
			b.customer AS customer,
			b.plot AS plot,
			b.project AS project,
			ps.stage_name AS stage_name,
			ps.amount_due AS amount_due,
			ps.amount_received AS amount_received,
			ps.balance AS balance,
			ps.due_date AS due_date
		FROM
			`tabRE Booking Payment Schedule` ps
		INNER JOIN `tabRE Booking` b ON ps.parent = b.name
		LEFT JOIN `tabRE Relationship Manager` rm ON b.assigned_rm = rm.name
		WHERE
			ps.status = 'Overdue'
			AND b.docstatus = 1
			{conditions}
		ORDER BY
			rm.rm_name, b.name, ps.due_date
	""".format(conditions=conditions),
		filters,
		as_dict=True,
	)

	for row in data:
		if row.due_date:
			row["days_overdue"] = date_diff(today, getdate(row.due_date))
		else:
			row["days_overdue"] = 0

	return data
