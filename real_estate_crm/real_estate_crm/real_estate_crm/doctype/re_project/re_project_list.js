frappe.listview_settings["RE Project"] = {
	onload: function (listview) {
		// Override row click to open project dashboard instead of form
		listview.$result.on("click", ".list-row-container", function (e) {
			// Don't intercept checkbox clicks or link clicks
			if ($(e.target).closest(".list-row-checkbox, .like-active-item").length) return;

			e.preventDefault();
			e.stopPropagation();

			let name = $(this).attr("data-name");
			if (name) {
				frappe.set_route("re-project-dashboard", name);
			}
		});
	},
};
