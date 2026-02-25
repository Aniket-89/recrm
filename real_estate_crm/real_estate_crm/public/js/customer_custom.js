// Extends the native Customer form with RE-specific features.
// Injected via doctype_js in hooks.py.

frappe.ui.form.on("Customer", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("View 360\u00b0"), () => {
				frappe.set_route("customer-360", frm.doc.name);
			});
		}
	},
});
