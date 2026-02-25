app_name = "real_estate_crm"
app_title = "Real Estate CRM"
app_publisher = "Placeholder Author"           # TODO: replace before go-live
app_description = "Real Estate CRM & Sales Management System on ERPNext"
app_email = "placeholder@example.com"          # TODO: replace before go-live
app_license = "MIT"
app_version = "0.0.1"

# ERPNext is a hard dependency — this app cannot run standalone
required_apps = ["frappe", "erpnext"]

# ─── Default Route ────────────────────────────────────────────────────────────
# When a user logs in, land on the CRM dashboard instead of the default desk.
default_route = "/app/re-dashboard"

# ─── Global Assets ────────────────────────────────────────────────────────────
# Loaded on every page — used for the persistent CRM sidebar and styling.
app_include_js = [
    "public/js/re_sidebar.js",
]
app_include_css = [
    "public/css/re_crm.css",
]

# ─── Install / Migrate ───────────────────────────────────────────────────────

after_install = "real_estate_crm.install.after_install"

# Re-applies custom fields on Lead, Opportunity, Customer after every migrate
# so they survive ERPNext core upgrades that reset custom fields.
after_migrate = "real_estate_crm.install.after_migrate"

# ─── Scheduled Jobs ──────────────────────────────────────────────────────────

scheduler_events = {
    # Marks overdue payment schedule rows and emails assigned RMs (PRD §7.4)
    "daily": [
        "real_estate_crm.tasks.mark_overdue_schedules",
    ],
}

# ─── Document Events ─────────────────────────────────────────────────────────
# Note: events on OUR OWN doctypes (RE Booking, RE Plot, etc.) are handled
# inside their controller classes — no registration needed here.
# Use doc_events only to hook into NATIVE ERPNext doctypes.

# ─── Client-side extensions for native doctypes ────────────────────────────
doctype_js = {
    "Customer": "public/js/customer_custom.js",
}

doc_events = {
    # Reserved for future use (e.g., Payment Entry hooks if needed)
}

# ─── Fixtures ────────────────────────────────────────────────────────────────
# Loaded automatically during `bench install-app` and `bench migrate`.
# The JSON files live in real_estate_crm/fixtures/.

fixtures = [
    {
        "dt": "Role",
        "filters": [
            [
                "name",
                "in",
                [
                    "RE Admin",
                    "RE Sales Manager",
                    "RE Sales Executive",
                    "RE Accounts",
                    "RE RM",
                ],
            ]
        ],
    },
    # Loaded after doctypes are synced — safe to list here even before
    # RE Document Type and RE Payment Plan Template doctypes are created.
    {"dt": "RE Document Type"},
    {"dt": "RE Payment Plan Template"},
]
