"""
RE Booking — core transaction doctype.
Lifecycle: Draft → (submit) → Booked → Payment In Progress → Possession Due → Completed
                              ↓ (cancel)
                           Cancelled
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, flt, cint, getdate, nowdate


class REBooking(Document):

    # ── Frappe lifecycle hooks ────────────────────────────────────────────────

    def validate(self):
        self._compute_final_value()
        self._validate_plot_availability()

    def before_submit(self):
        self._validate_possession_date_if_needed()
        self._generate_payment_schedule()

    def on_submit(self):
        self._lock_plot()
        frappe.db.set_value("RE Booking", self.name, "booking_status", "Booked")

    def on_cancel(self):
        self._release_plot()
        self._cancel_pending_schedule_rows()
        frappe.db.set_value("RE Booking", self.name, "booking_status", "Cancelled")

    # ── Validation helpers ────────────────────────────────────────────────────

    def _compute_final_value(self):
        self.final_value = flt(self.plot_value) - flt(self.discount)
        if self.final_value < 0:
            frappe.throw(_("Discount cannot exceed Plot Value."), title=_("Invalid Discount"))

    def _validate_plot_availability(self):
        """Block saving if the selected plot is already booked by another booking."""
        if not self.plot:
            return
        plot_status, existing_booking = frappe.db.get_value(
            "RE Plot", self.plot, ["status", "booking"]
        ) or ("", "")

        if plot_status in ("Booked", "Registered") and existing_booking != self.name:
            frappe.throw(
                _("Plot {0} is {1} under booking {2}. Select an Available plot.").format(
                    self.plot, plot_status, existing_booking
                ),
                title=_("Plot Not Available"),
            )

    def _validate_possession_date_if_needed(self):
        """Possession date is mandatory when the plan has possession-linked stages."""
        if not self.payment_plan_type:
            frappe.throw(_("Payment Plan is required before submitting."))
        if not self.final_value or flt(self.final_value) <= 0:
            frappe.throw(_("Final Value must be greater than zero before submitting."))

        has_possession_stage = frappe.db.exists(
            "RE Payment Plan Stage",
            {
                "parent": self.payment_plan_type,
                "due_trigger": ["in", ["On Possession", "Days from Possession"]],
            },
        )
        if has_possession_stage and not self.possession_date:
            frappe.throw(
                _(
                    "Possession Date is required — the selected payment plan has "
                    "possession-linked stages."
                ),
                title=_("Possession Date Required"),
            )

    # ── Payment schedule generation ───────────────────────────────────────────

    def _generate_payment_schedule(self):
        """
        Build RE Booking Payment Schedule rows from the selected
        RE Payment Plan Template. Called in before_submit so rows are
        committed in the same transaction. (PRD §7.2)
        """
        template = frappe.get_doc("RE Payment Plan Template", self.payment_plan_type)
        self.set("payment_schedule", [])

        for stage in sorted(template.stages, key=lambda s: s.stage_order or 0):
            amount_due = flt(self.final_value) * flt(stage.percentage) / 100.0
            due_date = self._due_date_for_stage(stage)
            self.append(
                "payment_schedule",
                {
                    "stage_name": stage.stage_name,
                    "stage_order": cint(stage.stage_order),
                    "percentage": flt(stage.percentage),
                    "amount_due": amount_due,
                    "due_date": due_date,
                    "amount_received": 0.0,
                    "balance": amount_due,
                    "status": "Pending",
                    "is_possession_stage": cint(stage.is_possession_stage),
                },
            )

    def _due_date_for_stage(self, stage):
        booking_date = getdate(self.booking_date)
        possession_date = getdate(self.possession_date) if self.possession_date else None

        trigger = stage.due_trigger
        if trigger == "On Booking":
            return booking_date
        elif trigger == "Days from Booking":
            return add_days(booking_date, cint(stage.due_days))
        elif trigger == "On Possession":
            return possession_date
        elif trigger == "Days from Possession":
            return add_days(possession_date, cint(stage.due_days))
        return booking_date

    # ── Plot state management ─────────────────────────────────────────────────

    def _lock_plot(self):
        """Mark the plot as Booked and link it to this booking. (PRD §5.2 on_submit)"""
        frappe.db.set_value(
            "RE Plot",
            self.plot,
            {"status": "Booked", "booking": self.name},
        )

    def _release_plot(self):
        """Revert plot to Available on booking cancellation. (PRD §5.2 on_cancel)"""
        frappe.db.set_value(
            "RE Plot",
            self.plot,
            {"status": "Available", "booking": None},
        )

    def _cancel_pending_schedule_rows(self):
        """Mark all non-Paid schedule rows as Cancelled."""
        frappe.db.sql(
            """
            UPDATE `tabRE Booking Payment Schedule`
            SET status = 'Cancelled'
            WHERE parent = %s AND status != 'Paid'
            """,
            self.name,
        )


# ── Whitelisted server methods ────────────────────────────────────────────────


@frappe.whitelist()
def receive_payment(
    booking_name,
    schedule_row_name,
    amount,
    payment_date,
    payment_mode,
    reference_no="",
):
    """
    Records a payment against a specific payment schedule stage.
    1. Creates an ERPNext Payment Entry.
    2. Updates the schedule row (amount_received, balance, status).
    3. Refreshes booking_status. (PRD §7.3)
    """
    amount = flt(amount)
    if amount <= 0:
        frappe.throw(_("Amount must be greater than zero."))

    booking = frappe.get_doc("RE Booking", booking_name)
    if booking.docstatus != 1:
        frappe.throw(_("Payments can only be recorded on a submitted booking."))

    # Locate the schedule row
    row = next(
        (r for r in booking.payment_schedule if r.name == schedule_row_name), None
    )
    if not row:
        frappe.throw(_("Payment schedule row not found."))
    if row.status == "Paid":
        frappe.throw(_("This stage is already fully paid."))

    max_receivable = flt(row.amount_due) - flt(row.amount_received)
    if amount > max_receivable + 0.01:
        frappe.throw(
            _("Amount {0} exceeds the balance due {1} for this stage.").format(
                frappe.utils.fmt_money(amount),
                frappe.utils.fmt_money(max_receivable),
            )
        )

    company = (
        frappe.defaults.get_user_default("Company")
        or frappe.db.get_single_value("Global Defaults", "default_company")
    )
    abbr = frappe.db.get_value("Company", company, "abbr")

    # Prefer RE-specific AR account; fall back to company default
    paid_from = frappe.db.get_value(
        "Account",
        {"name": f"Accounts Receivable - Real Estate - {abbr}", "company": company},
        "name",
    ) or frappe.db.get_value("Company", company, "default_receivable_account")

    # Bank/cash account from Mode of Payment → company mapping
    paid_to = frappe.db.get_value(
        "Mode of Payment Account",
        {"parent": payment_mode, "company": company},
        "default_account",
    ) or frappe.db.get_value("Company", company, "default_bank_account")

    if not paid_to:
        frappe.throw(
            _(
                "No bank/cash account found for payment mode '{0}' and company '{1}'. "
                "Configure it in Mode of Payment."
            ).format(payment_mode, company)
        )

    pe = frappe.get_doc(
        {
            "doctype": "Payment Entry",
            "payment_type": "Receive",
            "posting_date": payment_date,
            "company": company,
            "mode_of_payment": payment_mode,
            "party_type": "Customer",
            "party": booking.customer,
            "paid_from": paid_from,
            "paid_to": paid_to,
            "paid_amount": amount,
            "received_amount": amount,
            "source_exchange_rate": 1,
            "target_exchange_rate": 1,
            "reference_no": reference_no,
            "reference_date": payment_date,
            "remarks": (
                f"Payment for RE Booking {booking_name} — {row.stage_name}"
            ),
        }
    )
    pe.insert(ignore_permissions=True)
    pe.submit()

    # Update schedule row
    new_received = flt(row.amount_received) + amount
    new_balance = max(flt(row.amount_due) - new_received, 0)
    new_status = "Paid" if new_balance <= 0.01 else "Partial"

    frappe.db.set_value(
        "RE Booking Payment Schedule",
        row.name,
        {
            "amount_received": new_received,
            "balance": new_balance,
            "status": new_status,
            "payment_entry": pe.name,
            "receipt_date": payment_date,
        },
    )

    _refresh_booking_status(booking_name)
    return pe.name


@frappe.whitelist()
def generate_invoice(booking_name):
    """
    Creates a native ERPNext Sales Invoice for the booking. (PRD §10.3)
    Visible to RE Accounts / RE Admin only (enforced in JS).
    """
    frappe.only_for(["RE Accounts", "RE Admin", "System Manager"])

    booking = frappe.get_doc("RE Booking", booking_name)
    if booking.docstatus != 1:
        frappe.throw(_("Invoice can only be generated for a submitted booking."))

    company = (
        frappe.defaults.get_user_default("Company")
        or frappe.db.get_single_value("Global Defaults", "default_company")
    )

    si = frappe.new_doc("Sales Invoice")
    si.customer = booking.customer
    si.posting_date = nowdate()
    si.due_date = nowdate()
    si.company = company

    si.append(
        "items",
        {
            "item_name": f"Plot {booking.plot}",
            "description": (
                f"Sale of Plot {booking.plot}, Project: {booking.project}\n"
                f"Booking Ref: {booking_name}"
            ),
            "qty": 1,
            "rate": flt(booking.final_value),
            "amount": flt(booking.final_value),
            # item_code intentionally omitted — set a default item in ERPNext
            # (e.g. "Plot Sale") or extend this method as needed.
        },
    )

    si.set_missing_values()
    si.insert(ignore_permissions=True)
    return si.name


# ── Internal helpers ──────────────────────────────────────────────────────────


def _refresh_booking_status(booking_name):
    """
    Derive booking_status from the payment schedule state. (PRD §5.2)

    Transitions:
      Booked  →  Payment In Progress  →  Possession Due  →  Completed
    """
    rows = frappe.db.get_all(
        "RE Booking Payment Schedule",
        filters={"parent": booking_name},
        fields=["status", "is_possession_stage"],
    )
    if not rows:
        return

    non_possession = [r for r in rows if not r.is_possession_stage]
    possession = [r for r in rows if r.is_possession_stage]

    all_paid = all(r.status == "Paid" for r in rows)
    non_possession_paid = non_possession and all(
        r.status == "Paid" for r in non_possession
    )
    any_activity = any(r.status in ("Paid", "Partial") for r in rows)

    if all_paid:
        new_status = "Completed"
    elif non_possession_paid and possession:
        new_status = "Possession Due"
    elif any_activity:
        new_status = "Payment In Progress"
    else:
        new_status = "Booked"

    frappe.db.set_value("RE Booking", booking_name, "booking_status", new_status)
