# Global Search Modal — Design

## Problem
Frappe's Awesome Bar mixes RE CRM results with all ERPNext/Frappe noise. Users need a focused, cross-doctype search for their real estate data.

## Solution
Custom Cmd+K style search modal with categorized results, triggered by keyboard shortcut or sidebar icon.

## Trigger
- **Keyboard shortcut:** Ctrl+K (overrides Frappe's Awesome Bar when on RE pages)
- **Sidebar icon:** Search icon at the top of the existing RE sidebar

## UI Behavior
- Centered overlay modal with a single text input
- Debounced input (300ms) after minimum 2 characters
- Results grouped by category: Projects, Plots, Bookings, RMs, Customers
- Max 5 results per category with "View all in list" link
- Each result row: icon + primary text + secondary text + status badge
- Click navigates: Projects → project dashboard, everything else → form
- Escape or click outside closes

## Searchable Doctypes

| Doctype | Search fields | Result preview |
|---------|--------------|----------------|
| RE Project | project_name, project_code, city | Name, city, status |
| RE Plot | plot_number, project, sector | Plot #, project, status, area |
| RE Booking | name, customer, plot, project | Booking ID, customer, plot, status |
| RE Relationship Manager | rm_name, rm_code, mobile, email | Name, designation, mobile |
| Customer | customer_name, mobile_no, email_id | Name, mobile, email |

## Backend
- Single whitelisted API: `global_search(query)`
- `LIKE %query%` on search fields per doctype
- Max 5 results per doctype, exact matches first
- Respects `frappe.has_permission`
- Returns `{ category, items: [{name, title, subtitle, badge, route}] }`

## Files
- **New:** `re_global_search.py` — backend API
- **New:** `re_global_search.js` — modal UI (globally loaded)
- **Modify:** `re_sidebar.js` — add search icon trigger
- **Modify:** `re_crm.css` — modal styling
- **Modify:** `hooks.py` — add JS to `app_include_js`
