"""
Scheduled background tasks for Real Estate CRM.
Registered in hooks.py under scheduler_events.
"""

import frappe
from frappe.utils import today


def mark_overdue_schedules():
    """
    Daily job (PRD §7.4):
    - Marks RE Booking Payment Schedule rows as 'Overdue' when due_date
      has passed and status is still Pending or Partial.
    - Sends email alert to the booking's assigned RM.

    Safe to run before Module 4 doctypes exist — exits early if the
    table is not yet present (e.g., during initial bench setup).
    """
    if not frappe.db.table_exists("RE Booking Payment Schedule"):
        return

    overdue = frappe.db.get_all(
        "RE Booking Payment Schedule",
        filters={
            "status": ["in", ["Pending", "Partial"]],
            "due_date": ["<", today()],
        },
        fields=["name", "parent"],
    )

    for row in overdue:
        frappe.db.set_value(
            "RE Booking Payment Schedule",
            row.name,
            "status",
            "Overdue",
            update_modified=False,
        )
        # TODO: send email to assigned RM — implement in Module 4 (§7.4)

    if overdue:
        frappe.db.commit()
