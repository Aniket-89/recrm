frappe.ui.form.on("RE Payment Plan Template", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.set_df_property("plan_code", "read_only", 1);
		}
	},
});

// Recompute total percentage live as the child table changes
frappe.ui.form.on("RE Payment Plan Stage", {
	percentage(frm) {
		update_total(frm);
	},
	stages_remove(frm) {
		update_total(frm);
	},
});

function update_total(frm) {
	const total = (frm.doc.stages || []).reduce(
		(sum, row) => sum + flt(row.percentage),
		0
	);
	frm.set_value("total_percentage", total);

	// Visual cue — turn the field red if not 100
	const field = frm.get_field("total_percentage");
	if (field && field.$input) {
		field.$input.toggleClass("text-danger", Math.abs(total - 100) > 0.01);
	}
}
