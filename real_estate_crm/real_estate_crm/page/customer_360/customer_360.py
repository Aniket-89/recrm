import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate, fmt_money, date_diff


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
        "relationship_manager": None,
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

    # Relationship Manager from RE Booking (most recent)
    rm = frappe.db.get_value(
        "RE Booking",
        {"customer": customer, "docstatus": ["!=", 2]},
        "relationship_manager",
        order_by="creation desc",
    )
    if rm:
        info["relationship_manager"] = rm
        info["rm_name"] = frappe.db.get_value(
            "RE Relationship Manager", rm, "full_name"
        )

    return info


def _get_bookings(customer):
    """Return all RE Bookings for the customer."""
    bookings = frappe.get_all(
        "RE Booking",
        filters={"customer": customer, "docstatus": ["!=", 2]},
        fields=[
            "name",
            "plot",
            "project",
            "payment_plan_type",
            "booking_date",
            "status",
            "total_sale_amount",
            "relationship_manager",
        ],
        order_by="booking_date desc",
    )

    for b in bookings:
        b["plot_label"] = b.get("plot") or ""
        b["project_label"] = b.get("project") or ""

    return bookings


def _get_payment_details(booking_name):
    """Calculate payment summary and overdue stages for a booking."""
    schedules = frappe.get_all(
        "RE Payment Schedule",
        filters={"parent": booking_name, "parenttype": "RE Booking"},
        fields=[
            "name",
            "stage_name",
            "due_date",
            "amount",
            "received_amount",
            "status",
        ],
        order_by="due_date asc",
    )

    total_due = 0.0
    total_received = 0.0
    total_outstanding = 0.0
    next_due_date = None
    next_due_amount = 0.0
    overdue = []
    today = getdate(nowdate())

    for s in schedules:
        amt = flt(s.get("amount"))
        received = flt(s.get("received_amount"))
        total_due += amt
        total_received += received
        outstanding = amt - received
        total_outstanding += outstanding

        status = (s.get("status") or "").lower()
        due_date = getdate(s.get("due_date")) if s.get("due_date") else None

        # Overdue detection
        if due_date and due_date < today and outstanding > 0 and status != "paid":
            overdue.append(
                {
                    "booking": booking_name,
                    "stage_name": s.get("stage_name"),
                    "due_date": s.get("due_date"),
                    "amount": amt,
                    "received": received,
                    "outstanding": outstanding,
                    "days_overdue": date_diff(today, due_date),
                }
            )

        # Next upcoming due
        if (
            due_date
            and due_date >= today
            and outstanding > 0
            and status != "paid"
            and next_due_date is None
        ):
            next_due_date = s.get("due_date")
            next_due_amount = outstanding

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

    # Documents attached to Customer (if the Customer doctype has RE Document Entry child)
    try:
        customer_docs = frappe.get_all(
            "RE Document Entry",
            filters={"parenttype": "Customer", "parent": customer},
            fields=["document_type", "document_name", "file_url", "parent", "parenttype"],
        )
        for d in customer_docs:
            d["source"] = "Customer"
            d["source_name"] = customer
            documents.append(d)
    except Exception:
        pass

    # Documents from all bookings
    bookings = frappe.get_all(
        "RE Booking",
        filters={"customer": customer, "docstatus": ["!=", 2]},
        pluck="name",
    )
    if bookings:
        try:
            booking_docs = frappe.get_all(
                "RE Document Entry",
                filters={
                    "parenttype": "RE Booking",
                    "parent": ["in", bookings],
                },
                fields=[
                    "document_type",
                    "document_name",
                    "file_url",
                    "parent",
                    "parenttype",
                ],
            )
            for d in booking_docs:
                d["source"] = "RE Booking"
                d["source_name"] = d["parent"]
                documents.append(d)
        except Exception:
            pass

    return documents


def _get_activity(customer):
    """Return recent comments and communications for the customer."""
    comments = frappe.get_all(
        "Comment",
        filters={
            "reference_doctype": "Customer",
            "reference_name": customer,
            "comment_type": ["in", ["Comment", "Info", "Edit"]],
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
                "comment_type": ["in", ["Comment", "Info", "Edit"]],
            },
            fields=[
                "comment_by",
                "content",
                "creation",
                "comment_type",
                "reference_name",
            ],
            order_by="creation desc",
            limit_page_length=20,
        )
        for c in booking_comments:
            c["source"] = c.get("reference_name")
        comments.extend(booking_comments)

    # Sort combined by creation desc
    comments.sort(key=lambda x: x.get("creation"), reverse=True)
    return comments[:30]
