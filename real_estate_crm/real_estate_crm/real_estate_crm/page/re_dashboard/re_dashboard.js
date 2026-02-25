frappe.pages["re-dashboard"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Real Estate Dashboard",
		single_column: true,
	});

	page.main.addClass("re-dashboard-page");
	$('<div class="re-dashboard-content"></div>').appendTo(page.main);
	page.$content = page.main.find(".re-dashboard-content");

	page.set_secondary_action("Refresh", () => load_dashboard(page), "refresh");
};

frappe.pages["re-dashboard"].on_page_show = function (wrapper) {
	let page = wrapper.page;
	load_dashboard(page);
};

function load_dashboard(page) {
	page.$content.html(
		'<div class="re-dash-loading"><div class="spinner-border text-primary"></div><p class="text-muted mt-3">Loading dashboard&hellip;</p></div>'
	);

	frappe.call({
		method: "real_estate_crm.real_estate_crm.page.re_dashboard.re_dashboard.get_dashboard_data",
		callback: function (r) {
			if (r.message) {
				render_dashboard(page, r.message);
			}
		},
		error: function () {
			page.$content.html(
				'<div class="re-dash-loading"><i class="fa fa-exclamation-triangle text-danger fa-2x"></i><p class="mt-3 text-muted">Failed to load dashboard data.</p></div>'
			);
		},
	});
}

/* ================================================================== */
/*  MASTER RENDER                                                      */
/* ================================================================== */
function render_dashboard(page, data) {
	page.$content.empty();

	let html = '<div class="re-dash-container">';

	// Greeting header
	html += render_greeting();

	// KPI Cards row
	html += render_kpi_cards(data.kpi_cards);

	// Two-column layout: Plot chart + Project summary
	html += '<div class="re-dash-row">';
	html += '<div class="re-dash-col-6">' + render_plot_chart(data.plot_status_breakdown) + "</div>";
	html += '<div class="re-dash-col-6">' + render_collections_chart(data.monthly_collections) + "</div>";
	html += "</div>";

	// Project summary table
	html += render_project_summary(data.project_summary);

	// Two-column: Overdue + Upcoming
	html += '<div class="re-dash-row">';
	html += '<div class="re-dash-col-6">' + render_overdue_payments(data.overdue_payments) + "</div>";
	html += '<div class="re-dash-col-6">' + render_upcoming_dues(data.upcoming_dues) + "</div>";
	html += "</div>";

	// Recent bookings
	html += render_recent_bookings(data.recent_bookings);

	html += "</div>"; // close container
	page.$content.html(html);

	// Render charts after DOM is ready
	setTimeout(() => {
		draw_plot_donut(data.plot_status_breakdown);
		draw_collections_bar(data.monthly_collections);
	}, 100);
}

/* ================================================================== */
/*  GREETING                                                           */
/* ================================================================== */
function render_greeting() {
	let hour = new Date().getHours();
	let greeting = hour < 12 ? "Good Morning" : hour < 17 ? "Good Afternoon" : "Good Evening";
	let user = frappe.session.user_fullname || "there";

	return `
	<div class="re-dash-greeting">
		<h3>${greeting}, ${user}</h3>
		<p class="text-muted">Here's your real estate overview for today.</p>
	</div>`;
}

/* ================================================================== */
/*  KPI CARDS                                                          */
/* ================================================================== */
function render_kpi_cards(kpi) {
	let cards = [
		{
			label: "Active Bookings",
			value: kpi.active_bookings,
			icon: "fa-bookmark",
			color: "#2490ef",
			link: "/app/re-booking?booking_status=%5B%22in%22%2C%5B%22Booked%22%2C%22Payment+In+Progress%22%2C%22Possession+Due%22%5D%5D",
		},
		{
			label: "Available Plots",
			value: kpi.available_plots + " / " + kpi.total_plots,
			icon: "fa-map-marker",
			color: "#29cd42",
			link: "/app/re-plot?status=Available",
		},
		{
			label: "Total Revenue",
			value: format_compact_currency(kpi.total_revenue),
			icon: "fa-line-chart",
			color: "#7c3aed",
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
			subtitle: "Pending collection",
		},
		{
			label: "Overdue",
			value: format_compact_currency(kpi.overdue_amount),
			icon: "fa-exclamation-triangle",
			color: kpi.overdue_amount > 0 ? "#e24c4c" : "#98a1b3",
			link: "/app/query-report/Overdue Payment Report",
		},
	];

	let html = '<div class="re-dash-kpi-grid">';
	cards.forEach((c) => {
		let clickable = c.link ? ` onclick="frappe.set_route('${c.link}')" style="cursor:pointer;"` : "";
		html += `
		<div class="re-dash-kpi-card"${clickable}>
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
function render_plot_chart(breakdown) {
	return `
	<div class="re-dash-card">
		<div class="re-dash-card-header">
			<h6>Plot Inventory</h6>
		</div>
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

	let colors = {
		Available: "#29cd42",
		Booked: "#2490ef",
		Registered: "#7c3aed",
		"On Hold": "#ecaa00",
	};

	let labels = breakdown.map((d) => d.status);
	let values = breakdown.map((d) => d.count);
	let chartColors = breakdown.map((d) => colors[d.status] || "#98a1b3");

	new frappe.Chart("#re-plot-chart", {
		data: {
			labels: labels,
			datasets: [{ values: values }],
		},
		type: "donut",
		height: 220,
		colors: chartColors,
	});

	// Legend
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
function render_collections_chart(collections) {
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
/*  PROJECT SUMMARY TABLE                                              */
/* ================================================================== */
function render_project_summary(projects) {
	if (!projects || !projects.length) {
		return `
		<div class="re-dash-card">
			<div class="re-dash-card-header"><h6>Projects Overview</h6></div>
			<div class="re-dash-card-body"><p class="text-muted text-center">No projects yet.</p></div>
		</div>`;
	}

	let rows = projects
		.map((p) => {
			let pct = p.total_plots > 0 ? Math.round(((p.booked + p.registered) / p.total_plots) * 100) : 0;
			return `
			<tr>
				<td><a href="/app/re-project/${encodeURIComponent(p.project)}">${p.project_name || p.project}</a></td>
				<td class="text-center">${p.total_plots}</td>
				<td class="text-center"><span class="re-dash-badge green">${p.available}</span></td>
				<td class="text-center"><span class="re-dash-badge blue">${p.booked}</span></td>
				<td class="text-center"><span class="re-dash-badge purple">${p.registered}</span></td>
				<td class="text-center"><span class="re-dash-badge yellow">${p.on_hold}</span></td>
				<td>
					<div class="re-dash-progress">
						<div class="re-dash-progress-bar" style="width:${pct}%;"></div>
					</div>
					<small class="text-muted">${pct}% sold</small>
				</td>
			</tr>`;
		})
		.join("");

	return `
	<div class="re-dash-card">
		<div class="re-dash-card-header">
			<h6>Projects Overview</h6>
			<a href="/app/re-project" class="re-dash-link">View All</a>
		</div>
		<div class="re-dash-card-body">
			<div class="table-responsive">
				<table class="re-dash-table">
					<thead>
						<tr>
							<th>Project</th>
							<th class="text-center">Total</th>
							<th class="text-center">Available</th>
							<th class="text-center">Booked</th>
							<th class="text-center">Registered</th>
							<th class="text-center">On Hold</th>
							<th>Progress</th>
						</tr>
					</thead>
					<tbody>${rows}</tbody>
				</table>
			</div>
		</div>
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
			<a href="/app/query-report/Overdue Payment Report" class="re-dash-link">View Report</a>
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
				<td>${b.project || "-"}</td>
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
			<a href="/app/re-booking" class="re-dash-link">View All</a>
		</div>
		<div class="re-dash-card-body">
			<div class="table-responsive">
				<table class="re-dash-table">
					<thead>
						<tr>
							<th>Booking</th>
							<th>Date</th>
							<th>Customer</th>
							<th>Project</th>
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
