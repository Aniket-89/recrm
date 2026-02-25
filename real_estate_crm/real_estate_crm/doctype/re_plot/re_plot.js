frappe.ui.form.on("RE Plot", {
	refresh(frm) {
		// Enforce read-only status for non-admin users (Python validate mirrors this)
		const is_admin = frappe.user.has_role(["RE Admin", "System Manager", "Administrator"]);
		if (!is_admin) {
			frm.set_df_property("status", "read_only", 1);
		}

		// Quick link to the active booking
		if (frm.doc.booking && !frm.is_new()) {
			frm.add_custom_button(__("View Booking"), () => {
				frappe.set_route("Form", "RE Booking", frm.doc.booking);
			});
		}
	},

	plot_area(frm) {
		calculate_total_value(frm);
	},

	rate_per_unit(frm) {
		calculate_total_value(frm);
	},
});

function calculate_total_value(frm) {
	const area = flt(frm.doc.plot_area);
	const rate = flt(frm.doc.rate_per_unit);
	frm.set_value("total_value", area * rate);
}
