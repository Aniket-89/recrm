# Copyright (c) 2026, Real Estate CRM and contributors
# For license information, please see license.txt

"""
Customer Ledger — per-customer payment history with running balance.
PRD §11.6
"""

import frappe
from frappe.utils import flt


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"fieldname": "date", "label": "Date", "fieldtype": "Date", "width": 110},
		{
			"fieldname": "payment_entry",
			"label": "Payment Entry",
			"fieldtype": "Link",
			"options": "Payment Entry",
			"width": 160,
		},
		{
			"fieldname": "booking_no",
			"label": "Booking No",
			"fieldtype": "Link",
			"options": "RE Booking",
			"width": 150,
		},
		{"fieldname": "stage_name", "label": "Stage Name", "fieldtype": "Data", "width": 150},
		{"fieldname": "amount", "label": "Amount", "fieldtype": "Currency", "width": 130},
		{"fieldname": "payment_mode", "label": "Payment Mode", "fieldtype": "Data", "width": 120},
		{"fieldname": "reference_no", "label": "Reference No", "fieldtype": "Data", "width": 140},
		{"fieldname": "balance_after", "label": "Balance After", "fieldtype": "Currency", "width": 140},
	]


def get_data(filters):
	if not filters or not filters.get("customer"):
		return []

	customer = filters["customer"]

	# Total due across all submitted, non-cancelled bookings for this customer
	booking_conditions = "b.customer = %(customer)s AND b.docstatus = 1 AND b.booking_status != 'Cancelled'"
	if filters.get("project"):
		booking_conditions += " AND b.project = %(project)s"

	total_due = flt(
		frappe.db.sql(
			"""
			SELECT IFNULL(SUM(b.final_value), 0)
			FROM `tabRE Booking` b
			WHERE {cond}
			""".format(cond=booking_conditions),
			filters,
		)[0][0]
	)

	# Get all paid schedule rows that have a linked Payment Entry
	# Join with Payment Entry for mode_of_payment and reference_no
	date_conditions = ""
	if filters.get("from_date"):
		date_conditions += " AND ps.receipt_date >= %(from_date)s"
	if filters.get("to_date"):
		date_conditions += " AND ps.receipt_date <= %(to_date)s"

	rows = frappe.db.sql(
		"""
		SELECT
			ps.receipt_date AS date,
			ps.payment_entry,
			ps.parent AS booking_no,
			ps.stage_name,
			ps.amount_received AS amount,
			pe.mode_of_payment AS payment_mode,
			pe.reference_no
		FROM `tabRE Booking Payment Schedule` ps
		INNER JOIN `tabRE Booking` b ON ps.parent = b.name
		LEFT JOIN `tabPayment Entry` pe ON pe.name = ps.payment_entry
		WHERE b.customer = %(customer)s
			AND b.docstatus = 1
			AND ps.payment_entry IS NOT NULL
			AND ps.payment_entry != ''
			{project_cond}
			{date_cond}
		ORDER BY ps.receipt_date, ps.stage_order
		""".format(
			project_cond=" AND b.project = %(project)s" if filters.get("project") else "",
			date_cond=date_conditions,
		),
		filters,
		as_dict=True,
	)

	# Compute opening cumulative received if from_date is set
	cumulative_received = 0.0
	if filters.get("from_date"):
		prior = frappe.db.sql(
			"""
			SELECT IFNULL(SUM(ps.amount_received), 0)
			FROM `tabRE Booking Payment Schedule` ps
			INNER JOIN `tabRE Booking` b ON ps.parent = b.name
			WHERE b.customer = %(customer)s
				AND b.docstatus = 1
				AND ps.payment_entry IS NOT NULL
				AND ps.payment_entry != ''
				AND ps.receipt_date < %(from_date)s
				{project_cond}
			""".format(
				project_cond=" AND b.project = %(project)s" if filters.get("project") else "",
			),
			filters,
		)
		cumulative_received = flt(prior[0][0]) if prior else 0.0

	# Running balance: total_due - cumulative payments
	for row in rows:
		cumulative_received += flt(row.amount)
		row["balance_after"] = total_due - cumulative_received

	return rows
