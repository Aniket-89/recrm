frappe.pages["re-project-dashboard"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Project Dashboard",
		single_column: true,
	});

	page.main.addClass("re-dashboard-page");
	$('<div class="re-dashboard-content"></div>').appendTo(page.main);
	page.$content = page.main.find(".re-dashboard-content");

	page.set_secondary_action("Refresh", () => load_project_dashboard(page), "refresh");
};

frappe.pages["re-project-dashboard"].on_page_show = function (wrapper) {
	let page = wrapper.page;
	load_project_dashboard(page);
};

function get_project_from_route() {
	let route = frappe.get_route();
	return route.length > 1 ? route[1] : null;
}

function load_project_dashboard(page) {
	let project = get_project_from_route();
	if (!project) {
		page.$content.html(
			'<div class="re-dash-loading"><i class="fa fa-exclamation-triangle text-warning fa-2x"></i><p class="mt-3 text-muted">No project specified. <a href="/app/re-dashboard">Go to Home Dashboard</a></p></div>'
		);
		return;
	}

	page.$content.html(
		'<div class="re-dash-loading"><div class="spinner-border text-primary"></div><p class="text-muted mt-3">Loading project dashboard&hellip;</p></div>'
	);

	frappe.call({
		method: "real_estate_crm.real_estate_crm.page.re_project_dashboard.re_project_dashboard.get_project_dashboard_data",
		args: { project: project },
		callback: function (r) {
			if (r.message) {
				render_project_dashboard(page, r.message);
			}
		},
		error: function () {
			page.$content.html(
				'<div class="re-dash-loading"><i class="fa fa-exclamation-triangle text-danger fa-2x"></i><p class="mt-3 text-muted">Failed to load project dashboard.</p></div>'
			);
		},
	});
}

/* ================================================================== */
/*  MASTER RENDER                                                      */
/* ================================================================== */
function render_project_dashboard(page, data) {
	let info = data.project_info;
	page.set_title(info.project_name || info.name);

	page.$content.empty();
	let html = '<div class="re-dash-container">';

	html += render_project_header(info);
	html += render_project_kpi_cards(data.kpi_cards);

	html += '<div class="re-dash-row">';
	html += '<div class="re-dash-col-6">' + render_plot_chart() + "</div>";
	html += '<div class="re-dash-col-6">' + render_collections_chart() + "</div>";
	html += "</div>";

	html += render_plot_inventory(data.plot_inventory);
	html += render_assigned_rms(data.assigned_rms);

	html += '<div class="re-dash-row">';
	html += '<div class="re-dash-col-6">' + render_overdue_payments(data.overdue_payments) + "</div>";
	html += '<div class="re-dash-col-6">' + render_upcoming_dues(data.upcoming_dues) + "</div>";
	html += "</div>";

	html += render_recent_bookings(data.recent_bookings);

	html += "</div>";
	page.$content.html(html);

	setTimeout(() => {
		draw_plot_donut(data.plot_status_breakdown);
		draw_collections_bar(data.monthly_collections);
	}, 100);
}

/* ================================================================== */
/*  PROJECT HEADER                                                     */
/* ================================================================== */
function render_project_header(info) {
	let status_colors = { Active: "green", Completed: "blue", "On Hold": "yellow" };
	let color = status_colors[info.status] || "gray";
	let location = [info.location, info.city, info.state].filter(Boolean).join(", ");

	return `
	<div class="re-dash-greeting">
		<a href="/app/re-dashboard" class="re-dash-link" style="font-size:0.85em;">
			<i class="fa fa-arrow-left"></i> Back to Home Dashboard
		</a>
		<h3 style="margin-top:8px;">${info.project_name || info.name}
			<span class="indicator-pill ${color}" style="font-size:0.5em; vertical-align:middle;">${info.status}</span>
		</h3>
		${location ? `<p class="text-muted"><i class="fa fa-map-marker"></i> ${location}</p>` : ""}
	</div>`;
}

/* ================================================================== */
/*  KPI CARDS                                                          */
/* ================================================================== */
function render_project_kpi_cards(kpi) {
	let cards = [
		{ label: "Total Plots", value: kpi.total_plots, icon: "fa-map-marker", color: "#2490ef" },
		{ label: "Available", value: kpi.available, icon: "fa-check-circle", color: "#29cd42" },
		{ label: "Booked", value: kpi.booked, icon: "fa-bookmark", color: "#2490ef" },
		{ label: "Registered", value: kpi.registered, icon: "fa-file-text", color: "#7c3aed" },
		{
			label: "Revenue",
			value: format_compact_currency(kpi.total_revenue),
			icon: "fa-line-chart",
			color: "#2490ef",
			subtitle: "Booked Value",
		},
		{
			label: "Collected",
			value: format_compact_currency(kpi.total_received),
			icon: "fa-check-circle",
			color: "#29cd42",
			subtitle: format_percent(kpi.total_received, kpi.total_revenue) + " of revenue",
		},
		{
			label: "Outstanding",
			value: format_compact_currency(kpi.total_outstanding),
			icon: "fa-clock-o",
			color: "#ecaa00",
		},
		{
			label: "Overdue",
			value: format_compact_currency(kpi.overdue_amount),
			icon: "fa-exclamation-triangle",
			color: kpi.overdue_amount > 0 ? "#e24c4c" : "#98a1b3",
		},
	];

	let html = '<div class="re-dash-kpi-grid">';
	cards.forEach((c) => {
		html += `
		<div class="re-dash-kpi-card">
			<div class="re-dash-kpi-icon" style="background:${c.color}15; color:${c.color};">
				<i class="fa ${c.icon}"></i>
			</div>
			<div class="re-dash-kpi-body">
				<div class="re-dash-kpi-label">${c.label}</div>
				<div class="re-dash-kpi-value">${c.value}</div>
				${c.subtitle ? `<div class="re-dash-kpi-subtitle">${c.subtitle}</div>` : ""}
			</div>
		</div>`;
	});
	html += "</div>";
	return html;
}

/* ================================================================== */
/*  PLOT STATUS DONUT CHART                                            */
/* ================================================================== */
function render_plot_chart() {
	return `
	<div class="re-dash-card">
		<div class="re-dash-card-header"><h6>Plot Inventory</h6></div>
		<div class="re-dash-card-body">
			<div id="re-plot-chart" style="height:240px;"></div>
			<div class="re-dash-chart-legend" id="re-plot-legend"></div>
		</div>
	</div>`;
}

function draw_plot_donut(breakdown) {
	if (!breakdown || !breakdown.length) {
		$("#re-plot-chart").html('<p class="text-muted text-center" style="padding-top:80px;">No plot data yet.</p>');
		return;
	}

	let colors = { Available: "#29cd42", Booked: "#2490ef", Registered: "#7c3aed", "On Hold": "#ecaa00" };
	let labels = breakdown.map((d) => d.status);
	let values = breakdown.map((d) => d.count);
	let chartColors = breakdown.map((d) => colors[d.status] || "#98a1b3");

	new frappe.Chart("#re-plot-chart", {
		data: { labels: labels, datasets: [{ values: values }] },
		type: "donut",
		height: 220,
		colors: chartColors,
	});

	let legendHtml = breakdown
		.map(
			(d) => `
		<span class="re-dash-legend-item">
			<span class="re-dash-legend-dot" style="background:${colors[d.status] || "#98a1b3"};"></span>
			${d.status}: <strong>${d.count}</strong>
		</span>`
		)
		.join("");
	$("#re-plot-legend").html(legendHtml);
}

/* ================================================================== */
/*  MONTHLY COLLECTIONS BAR CHART                                      */
/* ================================================================== */
function render_collections_chart() {
	return `
	<div class="re-dash-card">
		<div class="re-dash-card-header">
			<h6>Monthly Collections</h6>
		</div>
		<div class="re-dash-card-body">
			<div id="re-collections-chart" style="height:240px;"></div>
		</div>
	</div>`;
}

function draw_collections_bar(collections) {
	if (!collections || !collections.length) {
		$("#re-collections-chart").html(
			'<p class="text-muted text-center" style="padding-top:80px;">No collection data yet.</p>'
		);
		return;
	}

	let labels = collections.map((d) => {
		let parts = d.month.split("-");
		let monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
		return monthNames[parseInt(parts[1]) - 1] + " " + parts[0].slice(2);
	});

	let values = collections.map((d) => d.collected);

	new frappe.Chart("#re-collections-chart", {
		data: {
			labels: labels,
			datasets: [{ name: "Collected", values: values }],
		},
		type: "bar",
		height: 220,
		colors: ["#29cd42"],
		barOptions: { spaceRatio: 0.4 },
		tooltipOptions: {
			formatTooltipY: (d) => format_compact_currency(d),
		},
	});
}

/* ================================================================== */
/*  PLOT INVENTORY TABLE                                               */
/* ================================================================== */
function render_plot_inventory(plots) {
	if (!plots || !plots.length) {
		return `
		<div class="re-dash-card">
			<div class="re-dash-card-header"><h6>Plot Inventory</h6></div>
			<div class="re-dash-card-body"><p class="text-muted text-center">No plots in this project.</p></div>
		</div>`;
	}

	let status_colors = { Available: "green", Booked: "blue", Registered: "purple", "On Hold": "yellow" };

	let rows = plots
		.map((pl) => {
			let color = status_colors[pl.status] || "gray";
			return `
			<tr>
				<td><a href="/app/re-plot/${encodeURIComponent(pl.name)}">${pl.plot_number}</a></td>
				<td>${pl.sector || "-"}</td>
				<td>${pl.plot_type || "-"}</td>
				<td class="text-right">${pl.plot_area} ${pl.area_unit}</td>
				<td class="text-right">${format_compact_currency(pl.total_value)}</td>
				<td><span class="re-dash-badge ${color}">${pl.status}</span></td>
				<td>${pl.customer || "-"}</td>
			</tr>`;
		})
		.join("");

	return `
	<div class="re-dash-card">
		<div class="re-dash-card-header">
			<h6>Plot Inventory</h6>
			<span class="text-muted" style="font-size:0.8em;">${plots.length} plots</span>
		</div>
		<div class="re-dash-card-body">
			<div class="table-responsive">
				<table class="re-dash-table">
					<thead>
						<tr>
							<th>Plot #</th>
							<th>Sector</th>
							<th>Type</th>
							<th class="text-right">Area</th>
							<th class="text-right">Value</th>
							<th>Status</th>
							<th>Customer</th>
						</tr>
					</thead>
					<tbody>${rows}</tbody>
				</table>
			</div>
		</div>
	</div>`;
}

/* ================================================================== */
/*  ASSIGNED RMs                                                       */
/* ================================================================== */
function render_assigned_rms(rms) {
	if (!rms || !rms.length) {
		return `
		<div class="re-dash-card">
			<div class="re-dash-card-header"><h6>Assigned Relationship Managers</h6></div>
			<div class="re-dash-card-body"><p class="text-muted text-center">No RMs assigned to this project.</p></div>
		</div>`;
	}

	let rows = rms
		.map(
			(rm) => `
		<div class="re-dash-list-item">
			<div class="re-dash-list-main">
				<a href="/app/re-relationship-manager/${encodeURIComponent(rm.name)}" class="re-dash-list-title">${rm.rm_name}</a>
				<div class="re-dash-list-meta">${rm.designation || "RM"} ${rm.mobile ? "&bull; " + rm.mobile : ""}</div>
			</div>
			<div class="re-dash-list-right">
				<span class="re-dash-badge blue">${rm.booking_count} bookings</span>
			</div>
		</div>`
		)
		.join("");

	return `
	<div class="re-dash-card">
		<div class="re-dash-card-header">
			<h6>Assigned Relationship Managers</h6>
		</div>
		<div class="re-dash-card-body re-dash-list">${rows}</div>
	</div>`;
}

/* ================================================================== */
/*  OVERDUE PAYMENTS                                                   */
/* ================================================================== */
function render_overdue_payments(overdues) {
	if (!overdues || !overdues.length) {
		return `
		<div class="re-dash-card">
			<div class="re-dash-card-header"><h6>Overdue Payments</h6></div>
			<div class="re-dash-card-body">
				<div class="re-dash-empty-state">
					<i class="fa fa-check-circle text-success fa-2x"></i>
					<p class="text-muted mt-2">No overdue payments!</p>
				</div>
			</div>
		</div>`;
	}

	let rows = overdues
		.map(
			(o) => `
		<div class="re-dash-list-item">
			<div class="re-dash-list-main">
				<a href="/app/re-booking/${encodeURIComponent(o.booking)}" class="re-dash-list-title">${o.booking}</a>
				<div class="re-dash-list-meta">${o.customer} &bull; ${o.stage_name}</div>
			</div>
			<div class="re-dash-list-right">
				<div class="re-dash-list-amount text-danger">${format_compact_currency(o.balance)}</div>
				<span class="re-dash-badge red">${o.days_overdue}d overdue</span>
			</div>
		</div>`
		)
		.join("");

	return `
	<div class="re-dash-card re-dash-card-danger">
		<div class="re-dash-card-header">
			<h6><i class="fa fa-exclamation-triangle text-danger"></i> Overdue Payments</h6>
		</div>
		<div class="re-dash-card-body re-dash-list">${rows}</div>
	</div>`;
}

/* ================================================================== */
/*  UPCOMING DUES                                                      */
/* ================================================================== */
function render_upcoming_dues(upcoming) {
	if (!upcoming || !upcoming.length) {
		return `
		<div class="re-dash-card">
			<div class="re-dash-card-header"><h6>Upcoming Dues (7 days)</h6></div>
			<div class="re-dash-card-body">
				<div class="re-dash-empty-state">
					<i class="fa fa-calendar-check-o text-muted fa-2x"></i>
					<p class="text-muted mt-2">No payments due this week.</p>
				</div>
			</div>
		</div>`;
	}

	let rows = upcoming
		.map(
			(u) => `
		<div class="re-dash-list-item">
			<div class="re-dash-list-main">
				<a href="/app/re-booking/${encodeURIComponent(u.booking)}" class="re-dash-list-title">${u.booking}</a>
				<div class="re-dash-list-meta">${u.customer} &bull; ${u.stage_name}</div>
			</div>
			<div class="re-dash-list-right">
				<div class="re-dash-list-amount">${format_compact_currency(u.balance)}</div>
				<small class="text-muted">${frappe.datetime.str_to_user(u.due_date)}</small>
			</div>
		</div>`
		)
		.join("");

	return `
	<div class="re-dash-card">
		<div class="re-dash-card-header">
			<h6><i class="fa fa-calendar text-primary"></i> Upcoming Dues (7 days)</h6>
		</div>
		<div class="re-dash-card-body re-dash-list">${rows}</div>
	</div>`;
}

/* ================================================================== */
/*  RECENT BOOKINGS                                                    */
/* ================================================================== */
function render_recent_bookings(bookings) {
	if (!bookings || !bookings.length) {
		return `
		<div class="re-dash-card">
			<div class="re-dash-card-header"><h6>Recent Bookings</h6></div>
			<div class="re-dash-card-body"><p class="text-muted text-center">No bookings yet.</p></div>
		</div>`;
	}

	let status_colors = {
		Draft: "gray",
		Booked: "blue",
		"Payment In Progress": "orange",
		"Possession Due": "yellow",
		Completed: "green",
		Cancelled: "red",
	};

	let rows = bookings
		.map((b) => {
			let color = status_colors[b.booking_status] || "gray";
			return `
			<tr>
				<td><a href="/app/re-booking/${encodeURIComponent(b.name)}">${b.name}</a></td>
				<td>${frappe.datetime.str_to_user(b.booking_date)}</td>
				<td>${b.customer || "-"}</td>
				<td>${b.plot || "-"}</td>
				<td class="text-right">${format_compact_currency(b.final_value)}</td>
				<td><span class="indicator-pill ${color}">${b.booking_status || "Draft"}</span></td>
			</tr>`;
		})
		.join("");

	return `
	<div class="re-dash-card">
		<div class="re-dash-card-header">
			<h6>Recent Bookings</h6>
		</div>
		<div class="re-dash-card-body">
			<div class="table-responsive">
				<table class="re-dash-table">
					<thead>
						<tr>
							<th>Booking</th>
							<th>Date</th>
							<th>Customer</th>
							<th>Plot</th>
							<th class="text-right">Value</th>
							<th>Status</th>
						</tr>
					</thead>
					<tbody>${rows}</tbody>
				</table>
			</div>
		</div>
	</div>`;
}

/* ================================================================== */
/*  HELPERS                                                            */
/* ================================================================== */
function format_compact_currency(value) {
	if (value === undefined || value === null || value === 0) return "0";
	if (Math.abs(value) >= 10000000) {
		return (value / 10000000).toFixed(2) + " Cr";
	} else if (Math.abs(value) >= 100000) {
		return (value / 100000).toFixed(2) + " L";
	} else if (Math.abs(value) >= 1000) {
		return (value / 1000).toFixed(1) + " K";
	}
	return frappe.format(value, { fieldtype: "Currency" });
}

function format_percent(part, total) {
	if (!total || total === 0) return "0%";
	return Math.round((part / total) * 100) + "%";
}
