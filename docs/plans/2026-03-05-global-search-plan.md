# Global Search Modal Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a Ctrl+K search modal that searches across RE Projects, Plots, Bookings, RMs, and Customers with categorized results.

**Architecture:** Single whitelisted Python API does `LIKE` queries on MariaDB across 5 doctypes, returns max 5 results per category. JS modal renders results grouped by category, triggered by Ctrl+K or sidebar search icon. All styling uses existing `re-dash-*` class conventions.

**Tech Stack:** Frappe framework (Python backend, jQuery/vanilla JS frontend), MariaDB `LIKE` queries.

---

### Task 1: Create Search Backend API

**Files:**
- Create: `real_estate_crm/real_estate_crm/api/re_global_search.py`

**Step 1: Create the API directory and file**

```bash
mkdir -p real_estate_crm/real_estate_crm/api
touch real_estate_crm/real_estate_crm/api/__init__.py
```

**Step 2: Write the search API**

```python
"""
Global Search API for Real Estate CRM.

Single endpoint that searches across RE Projects, Plots, Bookings,
Relationship Managers, and Customers. Returns max 5 results per category.
"""

import frappe
from frappe.utils import cstr


SEARCH_CONFIG = [
    {
        "doctype": "RE Project",
        "category": "Projects",
        "fields": ["name", "project_name", "project_code", "city", "status"],
        "search_fields": ["project_name", "project_code", "city"],
        "title_field": "project_name",
        "subtitle_fields": ["city", "status"],
        "badge_field": "status",
        "route_template": "/app/re-project-dashboard/{name}",
        "icon": "fa-folder-open",
    },
    {
        "doctype": "RE Plot",
        "category": "Plots",
        "fields": ["name", "plot_number", "project", "sector", "status", "plot_area", "area_unit"],
        "search_fields": ["plot_number", "project", "sector"],
        "title_field": "plot_number",
        "subtitle_fields": ["project", "plot_area", "area_unit"],
        "badge_field": "status",
        "route_template": "/app/re-plot/{name}",
        "icon": "fa-map-marker",
    },
    {
        "doctype": "RE Booking",
        "category": "Bookings",
        "fields": ["name", "customer", "plot", "project", "booking_status", "final_value"],
        "search_fields": ["name", "customer", "plot", "project"],
        "title_field": "name",
        "subtitle_fields": ["customer", "plot", "project"],
        "badge_field": "booking_status",
        "route_template": "/app/re-booking/{name}",
        "icon": "fa-bookmark",
    },
    {
        "doctype": "RE Relationship Manager",
        "category": "Relationship Managers",
        "fields": ["name", "rm_name", "rm_code", "mobile", "email", "designation", "status"],
        "search_fields": ["rm_name", "rm_code", "mobile", "email"],
        "title_field": "rm_name",
        "subtitle_fields": ["designation", "mobile"],
        "badge_field": "status",
        "route_template": "/app/re-relationship-manager/{name}",
        "icon": "fa-user-tie",
    },
    {
        "doctype": "Customer",
        "category": "Customers",
        "fields": ["name", "customer_name", "mobile_no", "email_id"],
        "search_fields": ["customer_name", "mobile_no", "email_id"],
        "title_field": "customer_name",
        "subtitle_fields": ["mobile_no", "email_id"],
        "badge_field": None,
        "route_template": "/app/customer/{name}",
        "icon": "fa-users",
    },
]


@frappe.whitelist()
def global_search(query):
    """Search across all RE CRM doctypes. Returns categorized results."""
    query = cstr(query).strip()
    if len(query) < 2:
        return []

    results = []
    for config in SEARCH_CONFIG:
        if not frappe.has_permission(config["doctype"], "read"):
            continue

        items = _search_doctype(query, config)
        if items:
            results.append({
                "category": config["category"],
                "icon": config["icon"],
                "doctype": config["doctype"],
                "items": items,
            })

    return results


def _search_doctype(query, config, limit=5):
    """Run LIKE search on a single doctype, exact matches first."""
    or_conditions = []
    params = {}

    for i, field in enumerate(config["search_fields"]):
        key_exact = f"q_exact_{i}"
        key_like = f"q_like_{i}"
        or_conditions.append(f"`{field}` = %({key_exact})s")
        or_conditions.append(f"`{field}` LIKE %({key_like})s")
        params[key_exact] = query
        params[key_like] = f"%{query}%"

    if not or_conditions:
        return []

    fields_sql = ", ".join(f"`{f}`" for f in config["fields"])
    doctype_table = f"`tab{config['doctype']}`"
    where_clause = " OR ".join(or_conditions)

    # Order: exact matches first (using a scoring trick), then alphabetical
    order_clauses = []
    for i, field in enumerate(config["search_fields"]):
        key_exact = f"q_exact_{i}"
        order_clauses.append(f"(`{field}` = %({key_exact})s) DESC")

    order_sql = ", ".join(order_clauses) + f", `{config['title_field']}` ASC"

    sql = f"""
        SELECT {fields_sql}
        FROM {doctype_table}
        WHERE ({where_clause})
        ORDER BY {order_sql}
        LIMIT {limit}
    """

    rows = frappe.db.sql(sql, params, as_dict=True)

    items = []
    for row in rows:
        subtitle_parts = [cstr(row.get(f)) for f in config["subtitle_fields"] if row.get(f)]
        item = {
            "name": row.get("name"),
            "title": row.get(config["title_field"]) or row.get("name"),
            "subtitle": " · ".join(subtitle_parts),
            "route": config["route_template"].format(**row),
        }
        if config["badge_field"] and row.get(config["badge_field"]):
            item["badge"] = row.get(config["badge_field"])
        items.append(item)

    return items
```

**Step 3: Commit**

```bash
git add real_estate_crm/real_estate_crm/api/
git commit -m "feat: add global search backend API"
```

---

### Task 2: Create Search Modal Frontend

**Files:**
- Create: `real_estate_crm/real_estate_crm/public/js/re_global_search.js`

**Step 1: Write the search modal JS**

```javascript
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

	// ── Build modal DOM (once) ──────────────────────────────────────
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

		// Close on overlay click
		$modal.on("click", function (e) {
			if ($(e.target).hasClass("re-search-overlay")) {
				close_search();
			}
		});

		// Input handler with debounce
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

		// Keyboard navigation
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

	// ── Search API call ─────────────────────────────────────────────
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

	// ── Render results ──────────────────────────────────────────────
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

			// "View all" link
			let list_route = "/app/" + cat.doctype.toLowerCase().replace(/ /g, "-");
			$section.append(`
				<a class="re-search-view-all" href="${list_route}">
					View all ${cat.category} →
				</a>`);

			$results.append($section);
		});
	}

	// ── Keyboard navigation ─────────────────────────────────────────
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
			// Scroll into view
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

	// ── Open / Close ────────────────────────────────────────────────
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

	// ── Global keybinding: Ctrl+K ───────────────────────────────────
	$(document).on("keydown", function (e) {
		if ((e.ctrlKey || e.metaKey) && e.key === "k") {
			e.preventDefault();
			e.stopPropagation();
			open_search();
		}
	});

	// ── Expose for sidebar icon ─────────────────────────────────────
	window.re_open_global_search = open_search;
})();
```

**Step 2: Commit**

```bash
git add real_estate_crm/real_estate_crm/public/js/re_global_search.js
git commit -m "feat: add global search modal frontend"
```

---

### Task 3: Add Search Modal CSS

**Files:**
- Modify: `real_estate_crm/real_estate_crm/public/css/re_crm.css`

**Step 1: Append search modal styles to the end of re_crm.css**

```css
/* ================================================================== */
/*  GLOBAL SEARCH MODAL                                                */
/* ================================================================== */

.re-search-overlay {
	position: fixed;
	inset: 0;
	background: rgba(0, 0, 0, 0.4);
	z-index: 10000;
	display: flex;
	justify-content: center;
	padding-top: 12vh;
}

.re-search-modal {
	width: 600px;
	max-width: 90vw;
	max-height: 70vh;
	background: var(--card-bg, #fff);
	border-radius: 12px;
	box-shadow: 0 16px 48px rgba(0, 0, 0, 0.2);
	display: flex;
	flex-direction: column;
	overflow: hidden;
}

.re-search-input-wrap {
	display: flex;
	align-items: center;
	padding: 14px 18px;
	border-bottom: 1px solid var(--border-color, #e2e8f0);
	gap: 10px;
}

.re-search-icon {
	color: var(--text-muted);
	font-size: 14px;
	flex-shrink: 0;
}

.re-search-input {
	flex: 1;
	border: none;
	outline: none;
	font-size: 1em;
	background: transparent;
	color: var(--text-color);
}

.re-search-input::placeholder {
	color: var(--text-muted);
}

.re-search-kbd {
	background: var(--bg-light-gray, #f1f5f9);
	border: 1px solid var(--border-color, #e2e8f0);
	border-radius: 4px;
	padding: 2px 6px;
	font-size: 0.7em;
	color: var(--text-muted);
	flex-shrink: 0;
}

.re-search-results {
	overflow-y: auto;
	flex: 1;
}

.re-search-loading {
	text-align: center;
	padding: 30px;
}

.re-search-empty {
	text-align: center;
	padding: 30px;
	color: var(--text-muted);
	font-size: 0.9em;
}

.re-search-category {
	border-bottom: 1px solid var(--border-color, #f0f0f0);
}

.re-search-category:last-child {
	border-bottom: none;
}

.re-search-category-header {
	padding: 8px 18px;
	font-size: 0.7em;
	text-transform: uppercase;
	letter-spacing: 0.8px;
	color: var(--text-muted);
	font-weight: 600;
	background: var(--bg-light-gray, #f8fafc);
}

.re-search-category-header i {
	margin-right: 4px;
	opacity: 0.7;
}

.re-search-item {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 10px 18px;
	cursor: pointer;
	transition: background 0.1s;
}

.re-search-item:hover,
.re-search-item-active {
	background: var(--bg-light-gray, #f0f4f8);
}

.re-search-item-main {
	min-width: 0;
}

.re-search-item-title {
	font-weight: 600;
	font-size: 0.9em;
	color: var(--text-color);
}

.re-search-item-subtitle {
	font-size: 0.78em;
	color: var(--text-muted);
	margin-top: 1px;
}

.re-search-badge {
	display: inline-block;
	padding: 2px 8px;
	border-radius: 10px;
	font-size: 0.72em;
	font-weight: 600;
	background: var(--bg-light-gray, #f1f5f9);
	color: var(--text-muted);
	flex-shrink: 0;
	margin-left: 8px;
}

.re-search-view-all {
	display: block;
	padding: 6px 18px 10px;
	font-size: 0.78em;
	color: var(--primary, #2490ef);
	text-decoration: none;
	font-weight: 500;
}

.re-search-view-all:hover {
	text-decoration: underline;
}
```

**Step 2: Commit**

```bash
git add real_estate_crm/real_estate_crm/public/css/re_crm.css
git commit -m "feat: add global search modal styles"
```

---

### Task 4: Add Search Icon to Sidebar and Register JS in Hooks

**Files:**
- Modify: `real_estate_crm/real_estate_crm/public/js/re_sidebar.js`
- Modify: `real_estate_crm/real_estate_crm/hooks.py`

**Step 1: Add search icon to the sidebar brand area**

In `re_sidebar.js`, inside `build_sidebar()`, add a search trigger after the brand div. Change the brand section to include a search icon:

```javascript
// Replace this line in sidebar_html:
//   <div class="re-sidebar-brand">
//       <i class="fa fa-building"></i> Real Estate CRM
//   </div>
// With:
		<div class="re-sidebar-brand">
			<i class="fa fa-building"></i> Real Estate CRM
		</div>

		<a class="re-sidebar-item re-sidebar-search" style="background:var(--bg-light-gray, #f1f5f9); margin: 4px 10px; border-radius: 6px; padding: 8px 14px;">
			<i class="fa fa-search"></i> Search
			<kbd style="margin-left:auto; background:var(--card-bg,#fff); border:1px solid var(--border-color,#e2e8f0); border-radius:3px; padding:1px 5px; font-size:0.75em; color:var(--text-muted);">Ctrl+K</kbd>
		</a>
```

Also add click handler after the existing sidebar click handler block:

```javascript
	// Search icon handler
	$(".re-crm-sidebar .re-sidebar-search").on("click", function (e) {
		e.preventDefault();
		if (window.re_open_global_search) {
			window.re_open_global_search();
		}
	});
```

**Step 2: Add the search JS to hooks.py `app_include_js`**

```python
app_include_js = [
    "/assets/real_estate_crm/js/re_sidebar.js",
    "/assets/real_estate_crm/js/re_global_search.js",
]
```

**Step 3: Commit**

```bash
git add real_estate_crm/real_estate_crm/public/js/re_sidebar.js real_estate_crm/real_estate_crm/hooks.py
git commit -m "feat: wire global search to sidebar and hooks"
```
