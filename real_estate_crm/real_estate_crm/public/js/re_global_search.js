/**
 * Real Estate CRM — Global Search Modal
 * Triggered by Ctrl+K or sidebar search icon.
 * Searches across Projects, Plots, Bookings, RMs, and Customers.
 */

(function () {
	let $modal = null;
	let $input = null;
	let $results = null;
	let debounce_timer = null;
	let selected_index = -1;
	let all_items = [];

	function ensure_modal() {
		if ($modal) return;

		$modal = $(`
		<div class="re-search-overlay" style="display:none;">
			<div class="re-search-modal">
				<div class="re-search-input-wrap">
					<i class="fa fa-search re-search-icon"></i>
					<input type="text" class="re-search-input" placeholder="Search projects, plots, bookings, RMs, customers..." autocomplete="off" />
					<kbd class="re-search-kbd">ESC</kbd>
				</div>
				<div class="re-search-results"></div>
			</div>
		</div>`);

		$("body").append($modal);
		$input = $modal.find(".re-search-input");
		$results = $modal.find(".re-search-results");

		$modal.on("click", function (e) {
			if ($(e.target).hasClass("re-search-overlay")) {
				close_search();
			}
		});

		$input.on("input", function () {
			let query = $(this).val().trim();
			clearTimeout(debounce_timer);

			if (query.length < 2) {
				$results.empty();
				selected_index = -1;
				all_items = [];
				return;
			}

			debounce_timer = setTimeout(() => do_search(query), 300);
		});

		$input.on("keydown", function (e) {
			if (e.key === "Escape") {
				close_search();
			} else if (e.key === "ArrowDown") {
				e.preventDefault();
				navigate(1);
			} else if (e.key === "ArrowUp") {
				e.preventDefault();
				navigate(-1);
			} else if (e.key === "Enter") {
				e.preventDefault();
				select_current();
			}
		});
	}

	function do_search(query) {
		$results.html('<div class="re-search-loading"><div class="spinner-border spinner-border-sm text-primary"></div></div>');

		frappe.call({
			method: "real_estate_crm.api.re_global_search.global_search",
			args: { query: query },
			callback: function (r) {
				render_results(r.message || []);
			},
			error: function () {
				$results.html('<div class="re-search-empty">Search failed. Please try again.</div>');
			},
		});
	}

	function render_results(categories) {
		$results.empty();
		selected_index = -1;
		all_items = [];

		if (!categories.length) {
			$results.html('<div class="re-search-empty">No results found</div>');
			return;
		}

		categories.forEach(function (cat) {
			let $section = $(`<div class="re-search-category">
				<div class="re-search-category-header">
					<i class="fa ${cat.icon}"></i> ${cat.category}
				</div>
			</div>`);

			cat.items.forEach(function (item) {
				let idx = all_items.length;
				all_items.push(item);

				let badge_html = item.badge
					? `<span class="re-search-badge">${item.badge}</span>`
					: "";

				let $item = $(`
				<div class="re-search-item" data-index="${idx}" data-route="${item.route}">
					<div class="re-search-item-main">
						<div class="re-search-item-title">${item.title}</div>
						<div class="re-search-item-subtitle">${item.subtitle || ""}</div>
					</div>
					${badge_html}
				</div>`);

				$item.on("click", function () {
					frappe.set_route($(this).data("route"));
					close_search();
				});

				$item.on("mouseenter", function () {
					selected_index = parseInt($(this).data("index"));
					update_selection();
				});

				$section.append($item);
			});

			let list_route = "/app/" + cat.doctype.toLowerCase().replace(/ /g, "-");
			$section.append(`
				<a class="re-search-view-all" href="${list_route}">
					View all ${cat.category} →
				</a>`);

			$results.append($section);
		});
	}

	function navigate(direction) {
		if (!all_items.length) return;
		selected_index += direction;
		if (selected_index < 0) selected_index = all_items.length - 1;
		if (selected_index >= all_items.length) selected_index = 0;
		update_selection();
	}

	function update_selection() {
		$results.find(".re-search-item").removeClass("re-search-item-active");
		if (selected_index >= 0) {
			let $active = $results.find(`.re-search-item[data-index="${selected_index}"]`);
			$active.addClass("re-search-item-active");
			let container = $results[0];
			let el = $active[0];
			if (el) {
				let top = el.offsetTop - container.offsetTop;
				if (top < container.scrollTop || top + el.offsetHeight > container.scrollTop + container.clientHeight) {
					el.scrollIntoView({ block: "nearest" });
				}
			}
		}
	}

	function select_current() {
		if (selected_index >= 0 && selected_index < all_items.length) {
			frappe.set_route(all_items[selected_index].route);
			close_search();
		}
	}

	function open_search() {
		ensure_modal();
		$modal.fadeIn(100);
		$input.val("").focus();
		$results.empty();
		selected_index = -1;
		all_items = [];
	}

	function close_search() {
		if ($modal) {
			$modal.fadeOut(100);
		}
	}

	$(document).on("keydown", function (e) {
		if ((e.ctrlKey || e.metaKey) && e.key === "k") {
			e.preventDefault();
			e.stopPropagation();
			open_search();
		}
	});

	window.re_open_global_search = open_search;
})();
