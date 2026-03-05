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
