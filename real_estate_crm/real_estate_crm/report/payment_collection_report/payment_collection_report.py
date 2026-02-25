# Copyright (c) 2026, Real Estate CRM and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, getdate, today


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"fieldname": "booking_no", "label": "Booking No", "fieldtype": "Link", "options": "RE Booking", "width": 140},
		{"fieldname": "customer", "label": "Customer", "fieldtype": "Link", "options": "Customer", "width": 150},
		{"fieldname": "plot", "label": "Plot", "fieldtype": "Link", "options": "RE Plot", "width": 130},
		{"fieldname": "stage_name", "label": "Stage Name", "fieldtype": "Data", "width": 150},
		{"fieldname": "stage_order", "label": "Stage Order", "fieldtype": "Int", "width": 90},
		{"fieldname": "amount_due", "label": "Amount Due", "fieldtype": "Currency", "width": 120},
		{"fieldname": "amount_received", "label": "Amount Received", "fieldtype": "Currency", "width": 130},
		{"fieldname": "balance", "label": "Balance", "fieldtype": "Currency", "width": 120},
		{"fieldname": "due_date", "label": "Due Date", "fieldtype": "Date", "width": 100},
		{"fieldname": "receipt_date", "label": "Receipt Date", "fieldtype": "Date", "width": 110},
		{"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 90},
	]


def get_data(filters):
	conditions = get_conditions(filters)

	data = frappe.db.sql(
		"""
		SELECT
			b.name AS booking_no,
			b.customer,
			b.plot,
			ps.stage_name,
			ps.stage_order,
			ps.amount_due,
			ps.amount_received,
			ps.balance,
			ps.due_date,
			ps.receipt_date,
			ps.status
		FROM `tabRE Booking` b
		INNER JOIN `tabRE Booking Payment Schedule` ps ON ps.parent = b.name AND ps.parenttype = 'RE Booking'
		LEFT JOIN `tabRE Relationship Manager` rm ON rm.name = b.assigned_rm
		WHERE b.docstatus = 1 {conditions}
		ORDER BY b.name, ps.stage_order
		""".format(conditions=conditions),
		filters,
		as_dict=True,
	)

	if not data:
		return data

	# Calculate totals for summary row
	total_due = sum(flt(row.get("amount_due")) for row in data)
	total_received = sum(flt(row.get("amount_received")) for row in data)
	total_balance = sum(flt(row.get("balance")) for row in data)

	# Append summary row
	data.append({
		"booking_no": "",
		"customer": "",
		"plot": "",
		"stage_name": "<b>Total</b>",
		"stage_order": None,
		"amount_due": total_due,
		"amount_received": total_received,
		"balance": total_balance,
		"due_date": None,
		"receipt_date": None,
		"status": "",
	})

	return data


def get_conditions(filters):
	conditions = ""

	if filters.get("project"):
		conditions += " AND b.project = %(project)s"

	if filters.get("assigned_rm"):
		conditions += " AND b.assigned_rm = %(assigned_rm)s"

	if filters.get("from_date"):
		conditions += " AND ps.due_date >= %(from_date)s"

	if filters.get("to_date"):
		conditions += " AND ps.due_date <= %(to_date)s"

	if filters.get("overdue_only"):
		conditions += " AND ps.status = 'Overdue'"

	return conditions
