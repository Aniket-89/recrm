"""
Install and migration hooks for Real Estate CRM.

after_install  → runs once on `bench install-app real_estate_crm`
after_migrate  → runs on every `bench migrate` (keeps custom fields alive)
"""

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_field


# ─── Public hooks (called from hooks.py) ─────────────────────────────────────


def after_install():
    create_custom_fields()
    create_chart_of_accounts()
    hide_default_workspaces()
    frappe.db.commit()


def after_migrate():
    """Re-apply custom fields so they survive ERPNext core upgrades."""
    create_custom_fields()
    hide_default_workspaces()
    frappe.db.commit()


# ─── Custom Fields ────────────────────────────────────────────────────────────


def create_custom_fields():
    """
    Adds RE-specific fields to native ERPNext doctypes.
    Idempotent — checks existence before creating.
    PRD §5.1 (Lead, Opportunity) and §8.3 (Customer Document Cabinet).
    """
    _CUSTOM_FIELDS = {
        "Lead": [
            {
                "fieldname": "re_interested_in_project",
                "label": "Interested in Project",
                "fieldtype": "Link",
                "options": "RE Project",
                "insert_after": "lead_name",
            },
            {
                "fieldname": "re_plot_preference",
                "label": "Plot Preference",
                "fieldtype": "Data",
                "description": "e.g. Corner, North Facing, 200 sqyd",
                "insert_after": "re_interested_in_project",
            },
            {
                "fieldname": "re_budget",
                "label": "Budget",
                "fieldtype": "Currency",
                "insert_after": "re_plot_preference",
            },
            {
                "fieldname": "re_assigned_rm",
                "label": "Assigned RM",
                "fieldtype": "Link",
                "options": "RE Relationship Manager",
                "insert_after": "re_budget",
            },
            {
                "fieldname": "re_lead_source_detail",
                "label": "Lead Source Detail",
                "fieldtype": "Data",
                "insert_after": "re_assigned_rm",
            },
        ],
        "Opportunity": [
            {
                "fieldname": "re_project",
                "label": "Project",
                "fieldtype": "Link",
                "options": "RE Project",
                "insert_after": "opportunity_from",
            },
            {
                "fieldname": "re_plot_shortlisted",
                "label": "Plot Shortlisted",
                "fieldtype": "Link",
                "options": "RE Plot",
                "insert_after": "re_project",
            },
            {
                "fieldname": "re_assigned_rm",
                "label": "Assigned RM",
                "fieldtype": "Link",
                "options": "RE Relationship Manager",
                "insert_after": "re_plot_shortlisted",
            },
        ],
        "Customer": [
            {
                "fieldname": "re_document_cabinet_section",
                "label": "Document Cabinet",
                "fieldtype": "Section Break",
                "insert_after": "loyalty_program_tier",
            },
            {
                "fieldname": "re_documents",
                "label": "Documents",
                "fieldtype": "Table",
                "options": "RE Document Entry",
                "insert_after": "re_document_cabinet_section",
            },
        ],
    }

    for doctype, fields in _CUSTOM_FIELDS.items():
        for field_def in fields:
            key = f"{doctype}-{field_def['fieldname']}"
            if not frappe.db.exists("Custom Field", key):
                field_def["dt"] = doctype
                create_custom_field(doctype, field_def)


# ─── Chart of Accounts ────────────────────────────────────────────────────────


def create_chart_of_accounts():
    """
    Creates RE-specific ledger accounts under the default company's COA.
    PRD §10.1.

    TODO: If the default company is not set, update Global Defaults in ERPNext
          and re-run: `bench execute real_estate_crm.install.create_chart_of_accounts`
    """
    company = frappe.db.get_single_value("Global Defaults", "default_company")
    if not company:
        frappe.log_error(
            "Real Estate CRM Install: No default company set in Global Defaults. "
            "Skipping COA setup. After configuring the company, run:\n"
            "  bench execute real_estate_crm.install.create_chart_of_accounts",
            title="RE CRM — COA Setup Skipped",
        )
        return

    abbr = frappe.db.get_value("Company", company, "abbr")

    # Income: Real Estate Revenue (group) → Plot Sales Revenue (ledger)
    income_root = _root_account(company, "Income")
    _ensure_account(company, abbr, "Real Estate Revenue", income_root, "Income Account", is_group=1)
    _ensure_account(
        company,
        abbr,
        "Plot Sales Revenue",
        f"Real Estate Revenue - {abbr}",
        "Income Account",
        is_group=0,
    )

    # Liability: Customer Advances (ledger)
    liability_root = _root_account(company, "Liability")
    _ensure_account(company, abbr, "Customer Advances", liability_root, "", is_group=0)

    # Asset: Accounts Receivable — Real Estate (ledger)
    asset_root = _root_account(company, "Asset")
    _ensure_account(
        company,
        abbr,
        "Accounts Receivable - Real Estate",
        asset_root,
        "Receivable",
        is_group=0,
    )


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _ensure_account(company, abbr, account_name, parent_account, account_type, is_group):
    full_name = f"{account_name} - {abbr}"
    if not frappe.db.exists("Account", full_name):
        frappe.get_doc(
            {
                "doctype": "Account",
                "account_name": account_name,
                "parent_account": parent_account,
                "company": company,
                "account_type": account_type,
                "is_group": is_group,
            }
        ).insert(ignore_permissions=True)


def _root_account(company, root_type):
    """Returns the top-level group account for a given root_type."""
    return frappe.db.get_value(
        "Account",
        {"company": company, "root_type": root_type, "parent_account": ("is", "not set")},
        "name",
    )


# ─── Hide Default Workspaces ────────────────────────────────────────────────


def hide_default_workspaces():
    """
    Hides all default ERPNext/Frappe workspaces except our Real Estate one.
    This makes the CRM the only visible module in the sidebar.
    Idempotent — safe to call on every migrate.
    """
    our_workspaces = ["Real Estate"]
    try:
        all_workspaces = frappe.get_all(
            "Workspace",
            filters={"is_standard": 1, "name": ["not in", our_workspaces]},
            pluck="name",
        )
        for ws_name in all_workspaces:
            frappe.db.set_value("Workspace", ws_name, "public", 0, update_modified=False)
    except Exception:
        # If Workspace table doesn't exist yet (fresh install), skip silently
        pass
