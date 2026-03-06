frappe.ui.form.on("RE Project", {
	onload(frm) {
		// Redirect to project dashboard unless explicitly editing
		if (!frm.is_new() && !frappe._re_edit_project) {
			frappe.set_route("re-project-dashboard", frm.doc.name);
			return;
		}
		frappe._re_edit_project = false;
	},

	refresh(frm) {
		// Lock project_code after first save — it is the document name
		if (!frm.is_new()) {
			frm.set_df_property("project_code", "read_only", 1);
		}

		// Shortcut button: open plots filtered to this project
		if (!frm.is_new()) {
			frm.add_custom_button(__("View Plots"), () => {
				frappe.set_route("List", "RE Plot", { project: frm.doc.name });
			});
			frm.add_custom_button(__("Project Dashboard"), () => {
				frappe.set_route("re-project-dashboard", frm.doc.name);
			});
		}
	},
});
