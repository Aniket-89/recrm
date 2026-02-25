// RE Booking — form controller
// PRD §5.2, §7.3, §10.3

frappe.ui.form.on("RE Booking", {
	// ── Setup ──────────────────────────────────────────────────────────────

	setup(frm) {
		// Only show Available plots for the selected project
		frm.set_query("plot", () => ({
			filters: {
				project: frm.doc.project,
				status: "Available",
			},
		}));

		// RM must be Active
		frm.set_query("assigned_rm", () => ({
			filters: { status: "Active" },
		}));
	},

	// ── Refresh ────────────────────────────────────────────────────────────

	refresh(frm) {
		const submitted = frm.doc.docstatus === 1;
		const cancelled = frm.doc.docstatus === 2;
		const is_accounts = frappe.user.has_role(["RE Accounts", "RE Admin", "System Manager"]);

		if (submitted && !cancelled) {
			// Receive Payment — visible to everyone who can read the form
			frm.add_custom_button(__("Receive Payment"), () => {
				open_payment_dialog(frm);
			}).addClass("btn-primary");

			// Generate Invoice — Accounts-only (PRD §10.3)
			if (is_accounts) {
				frm.add_custom_button(__("Generate Invoice"), () => {
					generate_invoice(frm);
				}, __("Actions"));
			}

			// Send Payment Reminder (stub — full implementation in Phase 2)
			frm.add_custom_button(__("Send Reminder"), () => {
				frappe.msgprint(__("Payment reminder email will be implemented in Phase 2."));
			}, __("Actions"));
		}

		// Status badge colour
		if (frm.doc.booking_status) {
			frm.dashboard.set_headline_alert(
				`<span class="indicator-pill ${status_colour(frm.doc.booking_status)} filterable">
					${frm.doc.booking_status}
				</span>`
			);
		}
	},

	// ── Field events ───────────────────────────────────────────────────────

	project(frm) {
		// Clear plot when project changes — previous plot may belong to old project
		frm.set_value("plot", "");
		frm.set_value("plot_value", 0);
		frm.set_value("final_value", 0);
	},

	plot(frm) {
		if (!frm.doc.plot) return;
		frappe.db.get_value("RE Plot", frm.doc.plot, "total_value", (r) => {
			if (r && r.total_value) {
				frm.set_value("plot_value", r.total_value);
			}
		});
	},

	plot_value(frm) {
		compute_final_value(frm);
	},

	discount(frm) {
		compute_final_value(frm);
	},
});

// ── Helpers ────────────────────────────────────────────────────────────────

function compute_final_value(frm) {
	const final = flt(frm.doc.plot_value) - flt(frm.doc.discount);
	frm.set_value("final_value", Math.max(final, 0));
}

function status_colour(status) {
	return (
		{
			Draft: "gray",
			Booked: "blue",
			"Payment In Progress": "orange",
			"Possession Due": "yellow",
			Completed: "green",
			Cancelled: "red",
		}[status] || "gray"
	);
}

// ── Receive Payment dialog ─────────────────────────────────────────────────

function open_payment_dialog(frm) {
	const pending = (frm.doc.payment_schedule || []).filter((r) =>
		["Pending", "Partial", "Overdue"].includes(r.status)
	);

	if (!pending.length) {
		frappe.msgprint(__("All payment stages are fully paid."));
		return;
	}

	// Build Select options: label shown in dropdown, value = row.name (child row ID)
	const stage_options = pending.map((r) => ({
		value: r.name,
		label: `${r.stage_name}  |  Due: ${r.due_date}  |  Balance: ${fmt_money(r.balance)}`,
	}));

	const dialog = new frappe.ui.Dialog({
		title: __("Receive Payment"),
		fields: [
			{
				label: __("Payment Stage"),
				fieldname: "schedule_row_name",
				fieldtype: "Select",
				options: stage_options.map((o) => o.value).join("\n"),
				reqd: 1,
				description: stage_options.map((o) => `${o.value}: ${o.label}`).join("<br>"),
			},
			{
				label: __("Amount Received"),
				fieldname: "amount",
				fieldtype: "Currency",
				reqd: 1,
				onchange() {
					// Show balance due for selected stage
					const sel = dialog.get_value("schedule_row_name");
					const row = pending.find((r) => r.name === sel);
					if (row) {
						const bal = flt(row.amount_due) - flt(row.amount_received);
						dialog.set_df_property(
							"amount",
							"description",
							__("Balance due: {0}", [fmt_money(bal)])
						);
					}
				},
			},
			{
				label: __("Payment Date"),
				fieldname: "payment_date",
				fieldtype: "Date",
				default: frappe.datetime.get_today(),
				reqd: 1,
			},
			{ fieldname: "col_break", fieldtype: "Column Break" },
			{
				label: __("Payment Mode"),
				fieldname: "payment_mode",
				fieldtype: "Select",
				options: "Cash\nCheque\nBank Transfer\nUPI",
				default: "Bank Transfer",
				reqd: 1,
			},
			{
				label: __("Reference / UTR No."),
				fieldname: "reference_no",
				fieldtype: "Data",
				description: __("Cheque number, UTR, transaction ID, etc."),
			},
		],
		primary_action_label: __("Record Payment"),
		primary_action(values) {
			frappe.call({
				method:
					"real_estate_crm.real_estate_crm.doctype.re_booking.re_booking.receive_payment",
				args: {
					booking_name: frm.doc.name,
					schedule_row_name: values.schedule_row_name,
					amount: values.amount,
					payment_date: values.payment_date,
					payment_mode: values.payment_mode,
					reference_no: values.reference_no || "",
				},
				freeze: true,
				freeze_message: __("Recording payment…"),
				callback(r) {
					if (r.message) {
						frappe.show_alert(
							{
								message: __("Payment recorded. PE: {0}", [r.message]),
								indicator: "green",
							},
							5
						);
						dialog.hide();
						frm.reload_doc();
					}
				},
			});
		},
	});

	// Pre-fill amount with full balance when a stage is chosen
	dialog.fields_dict.schedule_row_name.$input.on("change", function () {
		const sel = dialog.get_value("schedule_row_name");
		const row = pending.find((r) => r.name === sel);
		if (row) {
			const bal = flt(row.amount_due) - flt(row.amount_received);
			dialog.set_value("amount", bal);
		}
	});

	dialog.show();
}

// ── Generate Invoice ───────────────────────────────────────────────────────

function generate_invoice(frm) {
	frappe.confirm(
		__("Generate a Sales Invoice for this booking?"),
		() => {
			frappe.call({
				method:
					"real_estate_crm.real_estate_crm.doctype.re_booking.re_booking.generate_invoice",
				args: { booking_name: frm.doc.name },
				freeze: true,
				freeze_message: __("Creating Sales Invoice…"),
				callback(r) {
					if (r.message) {
						frappe.show_alert(
							{ message: __("Invoice {0} created.", [r.message]), indicator: "green" },
							5
						);
						frappe.set_route("Form", "Sales Invoice", r.message);
					}
				},
			});
		}
	);
}

function fmt_money(val) {
	return frappe.utils.format_number(flt(val), null, 2);
}
