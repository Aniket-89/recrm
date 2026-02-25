"""
Customer 360 — single-screen view of everything about a customer.
PRD §9.1
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate, date_diff


@frappe.whitelist()
def get_customer_360_data(customer):
    """Return all Customer 360 data for the given customer."""
    if not customer:
        frappe.throw(_("Please select a customer."))

    data = {
        "customer_info": _get_customer_info(customer),
        "bookings": _get_bookings(customer),
        "payment_summary": {},
        "overdue_stages": [],
        "documents": _get_documents(customer),
        "activity": _get_activity(customer),
    }

    # Build payment summary and overdue stages per booking
    for booking in data["bookings"]:
        summary, overdue = _get_payment_details(booking["name"])
        data["payment_summary"][booking["name"]] = summary
        if overdue:
            data["overdue_stages"].extend(overdue)

    return data


def _get_customer_info(customer):
    """Fetch customer master info, primary contact, address and assigned RM."""
    cust = frappe.get_doc("Customer", customer)

    info = {
        "customer_name": cust.customer_name,
        "name": cust.name,
        "email": None,
        "mobile": None,
        "address": None,
        "assigned_rm": None,
        "rm_name": None,
    }

    # Primary contact
    contact_name = frappe.db.get_value(
        "Dynamic Link",
        {"link_doctype": "Customer", "link_name": customer, "parenttype": "Contact"},
        "parent",
    )
    if contact_name:
        contact = frappe.get_doc("Contact", contact_name)
        info["email"] = contact.email_id
        info["mobile"] = contact.mobile_no

    # Primary address
    address_name = frappe.db.get_value(
        "Dynamic Link",
        {"link_doctype": "Customer", "link_name": customer, "parenttype": "Address"},
        "parent",
    )
    if address_name:
        from frappe.contacts.doctype.address.address import get_address_display
        info["address"] = get_address_display(address_name)

    # Relationship Manager from most recent RE Booking
    rm = frappe.db.get_value(
        "RE Booking",
        {"customer": customer, "docstatus": ["!=", 2]},
        "assigned_rm",
        order_by="creation desc",
    )
    if rm:
        info["assigned_rm"] = rm
        info["rm_name"] = frappe.db.get_value(
            "RE Relationship Manager", rm, "rm_name"
        )

    return info


def _get_bookings(customer):
    """Return all RE Bookings for the customer."""
    return frappe.get_all(
        "RE Booking",
        filters={"customer": customer, "docstatus": ["!=", 2]},
        fields=[
            "name",
            "plot",
            "project",
            "payment_plan_type",
            "booking_date",
            "booking_status",
            "final_value",
            "assigned_rm",
        ],
        order_by="booking_date desc",
    )


def _get_payment_details(booking_name):
    """Calculate payment summary and overdue stages for a booking."""
    schedules = frappe.get_all(
        "RE Booking Payment Schedule",
        filters={"parent": booking_name, "parenttype": "RE Booking"},
        fields=[
            "name",
            "stage_name",
            "due_date",
            "amount_due",
            "amount_received",
            "balance",
            "status",
        ],
        order_by="stage_order asc",
    )

    total_due = 0.0
    total_received = 0.0
    total_outstanding = 0.0
    next_due_date = None
    next_due_amount = 0.0
    overdue = []
    today = getdate(nowdate())

    for s in schedules:
        amt = flt(s.amount_due)
        received = flt(s.amount_received)
        bal = flt(s.balance)
        total_due += amt
        total_received += received
        total_outstanding += bal

        due_date = getdate(s.due_date) if s.due_date else None

        # Overdue detection
        if s.status == "Overdue" or (
            due_date and due_date < today and bal > 0 and s.status != "Paid"
        ):
            overdue.append({
                "booking": booking_name,
                "stage_name": s.stage_name,
                "due_date": str(s.due_date) if s.due_date else None,
                "amount_due": amt,
                "received": received,
                "outstanding": bal,
                "days_overdue": date_diff(today, due_date) if due_date else 0,
            })

        # Next upcoming due
        if (
            due_date
            and due_date >= today
            and bal > 0
            and s.status not in ("Paid", "Cancelled")
            and next_due_date is None
        ):
            next_due_date = str(s.due_date)
            next_due_amount = bal

    summary = {
        "total_due": total_due,
        "total_received": total_received,
        "total_outstanding": total_outstanding,
        "next_due_date": next_due_date,
        "next_due_amount": next_due_amount,
    }

    return summary, overdue


def _get_documents(customer):
    """Collect documents from customer and all bookings (RE Document Entry child table)."""
    documents = []

    # Documents attached to Customer
    customer_docs = frappe.get_all(
        "RE Document Entry",
        filters={"parenttype": "Customer", "parent": customer},
        fields=["document_type", "document_name", "file", "uploaded_on", "remarks"],
    )
    for d in customer_docs:
        d["source"] = "Customer"
        d["source_name"] = customer
        documents.append(d)

    # Documents from all bookings
    bookings = frappe.get_all(
        "RE Booking",
        filters={"customer": customer, "docstatus": ["!=", 2]},
        pluck="name",
    )
    if bookings:
        booking_docs = frappe.get_all(
            "RE Document Entry",
            filters={
                "parenttype": "RE Booking",
                "parent": ["in", bookings],
            },
            fields=["document_type", "document_name", "file", "uploaded_on", "remarks", "parent"],
        )
        for d in booking_docs:
            d["source"] = "RE Booking"
            d["source_name"] = d["parent"]
            documents.append(d)

    return documents


def _get_activity(customer):
    """Return recent comments and communications for the customer."""
    comments = frappe.get_all(
        "Comment",
        filters={
            "reference_doctype": "Customer",
            "reference_name": customer,
            "comment_type": ["in", ["Comment", "Info"]],
        },
        fields=["comment_by", "content", "creation", "comment_type"],
        order_by="creation desc",
        limit_page_length=20,
    )

    # Also get comments on bookings
    bookings = frappe.get_all(
        "RE Booking",
        filters={"customer": customer, "docstatus": ["!=", 2]},
        pluck="name",
    )
    if bookings:
        booking_comments = frappe.get_all(
            "Comment",
            filters={
                "reference_doctype": "RE Booking",
                "reference_name": ["in", bookings],
                "comment_type": ["in", ["Comment", "Info"]],
            },
            fields=[
                "comment_by", "content", "creation",
                "comment_type", "reference_name",
            ],
            order_by="creation desc",
            limit_page_length=20,
        )
        for c in booking_comments:
            c["source"] = c.get("reference_name")
        comments.extend(booking_comments)

    # Sort combined by creation desc
    comments.sort(key=lambda x: x.get("creation") or "", reverse=True)
    return comments[:30]
