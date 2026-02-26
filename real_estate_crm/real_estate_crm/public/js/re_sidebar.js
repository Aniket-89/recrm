/**
 * Real Estate CRM — Persistent Sidebar
 * Injected on all pages via app_include_js in hooks.py.
 * Provides consistent CRM navigation across the entire app.
 */

$(document).on("startup", function () {
	// startup event fires after frappe.boot is loaded and desk is ready
	if (frappe.session.user === "Guest") return;

	build_sidebar();

	// Update active state on route change
	frappe.router.on("change", function () {
		build_sidebar();
		update_active_item();
	});
});

function build_sidebar() {
	// Don't create duplicate
	if ($(".re-crm-sidebar").length) return;

	let sidebar_html = `
	<nav class="re-crm-sidebar">
		<div class="re-sidebar-brand">
			<i class="fa fa-building"></i> Real Estate CRM
		</div>

		<a class="re-sidebar-item" data-route="/app/re-dashboard">
			<i class="fa fa-tachometer"></i> Dashboard
		</a>

		<div class="re-sidebar-section">Manage</div>
		<a class="re-sidebar-item" data-route="/app/re-project">
			<i class="fa fa-folder-open"></i> Projects
		</a>
		<a class="re-sidebar-item" data-route="/app/re-plot">
			<i class="fa fa-map-marker"></i> Plots
		</a>
		<a class="re-sidebar-item" data-route="/app/re-booking">
			<i class="fa fa-bookmark"></i> Bookings
		</a>
		<a class="re-sidebar-item" data-route="/app/customer">
			<i class="fa fa-users"></i> Customers
		</a>
		<a class="re-sidebar-item" data-route="/app/re-relationship-manager">
			<i class="fa fa-user-tie"></i> RM
		</a>

		<div class="re-sidebar-divider"></div>

		<div class="re-sidebar-section">Reports</div>
		<a class="re-sidebar-item" data-route="/app/query-report/Plot Inventory Status">
			<i class="fa fa-bar-chart"></i> Plot Inventory
		</a>
		<a class="re-sidebar-item" data-route="/app/query-report/Booking Register">
			<i class="fa fa-list"></i> Booking Register
		</a>
		<a class="re-sidebar-item" data-route="/app/query-report/Payment Collection Report">
			<i class="fa fa-money"></i> Collections
		</a>
		<a class="re-sidebar-item" data-route="/app/query-report/Overdue Payment Report">
			<i class="fa fa-exclamation-circle"></i> Overdue
		</a>
		<a class="re-sidebar-item" data-route="/app/query-report/RM Performance Report">
			<i class="fa fa-line-chart"></i> RM Performance
		</a>
		<a class="re-sidebar-item" data-route="/app/query-report/Customer Ledger">
			<i class="fa fa-book"></i> Customer Ledger
		</a>

		<div class="re-sidebar-divider"></div>

		<div class="re-sidebar-section">Tools</div>
		<a class="re-sidebar-item" data-route="/app/customer-360">
			<i class="fa fa-user-circle"></i> Customer 360
		</a>
		<a class="re-sidebar-item" data-route="/app/re-payment-plan-template">
			<i class="fa fa-calendar-check-o"></i> Payment Plans
		</a>
		<a class="re-sidebar-item" data-route="/app/re-document-type">
			<i class="fa fa-file-text-o"></i> Document Types
		</a>
	</nav>

	<button class="re-sidebar-toggle" onclick="$('.re-crm-sidebar').toggleClass('re-sidebar-open');">
		<i class="fa fa-bars"></i>
	</button>`;

	$("body").append(sidebar_html);
	$("body").addClass("re-has-sidebar");

	// Click handlers — use Frappe routing
	$(".re-crm-sidebar .re-sidebar-item").on("click", function (e) {
		e.preventDefault();
		let route = $(this).data("route");
		if (route) {
			frappe.set_route(route);
			$(".re-crm-sidebar").removeClass("re-sidebar-open");
		}
	});

	update_active_item();
}

function update_active_item() {
	let path = window.location.pathname;

	$(".re-crm-sidebar .re-sidebar-item").removeClass("active");
	$(".re-crm-sidebar .re-sidebar-item").each(function () {
		let item_route = $(this).data("route");
		if (!item_route) return;

		if (path === item_route || path.startsWith(item_route + "/")) {
			$(this).addClass("active");
		}
	});
}
