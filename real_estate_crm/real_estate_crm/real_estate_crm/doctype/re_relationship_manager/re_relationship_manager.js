frappe.ui.form.on("RE Relationship Manager", {
	refresh(frm) {
		if (!frm.is_new()) {
			load_dashboard(frm);
		}
	},
});

function load_dashboard(frm) {
	frappe.call({
		method: "get_performance_stats",
		doc: frm.doc,
		callback(r) {
			if (!r.message) return;
			const stats = r.message;

			const active_rows = (stats.active_bookings || [])
				.map(
					(b) =>
						`<tr>
							<td>${b.name}</td>
							<td>${b.project || ""}</td>
							<td>${b.plot || ""}</td>
							<td><span class="indicator-pill ${status_color(b.booking_status)}">${b.booking_status}</span></td>
						</tr>`
				)
				.join("");

			const html = `
				<div class="row" style="margin-bottom:12px">
					<div class="col-sm-3">
						<div class="stat-box text-center p-3 border rounded">
							<div class="h3 text-primary">${stats.leads}</div>
							<div class="text-muted small">${__("Leads Assigned")}</div>
						</div>
					</div>
					<div class="col-sm-3">
						<div class="stat-box text-center p-3 border rounded">
							<div class="h3 text-success">${stats.closed_bookings}</div>
							<div class="text-muted small">${__("Bookings Closed")}</div>
						</div>
					</div>
					<div class="col-sm-3">
						<div class="stat-box text-center p-3 border rounded">
							<div class="h3 text-warning">${stats.active_bookings.length}</div>
							<div class="text-muted small">${__("Active Bookings")}</div>
						</div>
					</div>
					<div class="col-sm-3">
						<div class="stat-box text-center p-3 border rounded">
							<div class="h3 text-info">${format_currency(stats.total_revenue)}</div>
							<div class="text-muted small">${__("Revenue Generated")}</div>
						</div>
					</div>
				</div>
				${
					active_rows
						? `<table class="table table-bordered table-sm">
								<thead><tr>
									<th>${__("Booking")}</th>
									<th>${__("Project")}</th>
									<th>${__("Plot")}</th>
									<th>${__("Status")}</th>
								</tr></thead>
								<tbody>${active_rows}</tbody>
							</table>`
						: `<p class="text-muted">${__("No active bookings.")}</p>`
				}
			`;
			frm.get_field("dashboard_html").$wrapper.html(html);
		},
	});
}

function status_color(status) {
	const map = {
		Booked: "blue",
		"Payment In Progress": "orange",
		"Possession Due": "yellow",
		Completed: "green",
		Cancelled: "red",
	};
	return map[status] || "gray";
}

function format_currency(val) {
	return frappe.utils.format_number(val, null, 0);
}
