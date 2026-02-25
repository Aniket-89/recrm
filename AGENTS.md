# Product Requirements Document

## Real Estate CRM & Sales Management System on ERPNext

-----

## 1. Project Overview

**Platform:** ERPNext (Frappe Framework)
**Industry:** Real Estate — Plot Sales
**Deployment:** Internal use (single company)
**Current Scale:** Single project, multi-project ready architecture required
**Integration:** ERPNext native accounting (replaces Tally)

### Goal

Build a fully integrated Real Estate CRM on top of ERPNext that manages the complete lifecycle — from lead capture to plot booking, payment plan tracking, document management, RM assignment, and accounting linkage — all within a single unified system.

-----

## 2. Architecture Principles

- All custom doctypes must be built as a **custom Frappe app** (e.g., `real_estate_crm`) installed on top of ERPNext. Do NOT modify core ERPNext files.
- Design with **multi-project support** from day one even though only one project exists currently. Every master and transaction doctype must have a `project` link field.
- All financial entries (payment receipts, dues) must post to **ERPNext’s native GL (General Ledger)** — no parallel accounting.
- Use ERPNext’s native **File attachment** system but extend it with a structured Document Cabinet child table per customer and per booking.
- Follow Frappe naming conventions, roles, permissions, and hooks throughout.

-----

## 3. Modules to Build

1. Project & Plot Master
1. CRM (Lead → Opportunity → Booking)
1. Relationship Manager (RM) Master
1. Payment Plan Engine
1. Document Cabinet
1. Customer 360 Dashboard
1. Accounting Integration
1. Reports

-----

## 4. Module 1 — Project & Plot Master

### 4.1 Doctype: `RE Project` (Real Estate Project)

|Field                   |Type       |Notes                       |
|------------------------|-----------|----------------------------|
|project_name            |Data       |Required                    |
|project_code            |Data       |Short code, used in naming  |
|location                |Data       |                            |
|city                    |Data       |                            |
|state                   |Data       |                            |
|total_plots             |Int        |                            |
|project_start_date      |Date       |                            |
|expected_possession_date|Date       |                            |
|status                  |Select     |Active / Completed / On Hold|
|description             |Text Editor|                            |

### 4.2 Doctype: `RE Plot`

|Field         |Type             |Notes                                       |
|--------------|-----------------|--------------------------------------------|
|plot_number   |Data             |Required, unique per project                |
|project       |Link → RE Project|Required                                    |
|sector / block|Data             |Optional grouping                           |
|plot_area     |Float            |In square yards (sqyd)                      |
|area_unit     |Select           |Sqyd / Sqft                                 |
|facing        |Select           |North / South / East / West / Corner / Other|
|plot_type     |Select           |Residential / Commercial                    |
|rate_per_unit |Currency         |Rate per sqyd or sqft                       |
|total_value   |Currency         |Auto-calculated: area × rate                |
|status        |Select           |Available / Booked / Registered / On Hold   |
|booking       |Link → RE Booking|Set automatically on booking                |
|remarks       |Text             |                                            |

**Validations:**

- `total_value` = `plot_area × rate_per_unit`, auto-computed on save.
- Status must only be changeable through the booking workflow, not manually (except by Admin role).
- A plot with status Booked/Registered must not be bookable again.

-----

## 5. Module 2 — CRM

### 5.1 Use ERPNext Native CRM for Leads and Opportunities

- Use existing ERPNext **Lead** and **Opportunity** doctypes.
- Add the following custom fields to **Lead**:
  - `interested_in_project` → Link to RE Project
  - `plot_preference` → Data (e.g., “Corner, North Facing, 200 sqyd”)
  - `budget` → Currency
  - `assigned_rm` → Link to RE Relationship Manager
  - `lead_source_detail` → Data
- Add the following custom fields to **Opportunity**:
  - `project` → Link to RE Project
  - `plot_shortlisted` → Link to RE Plot
  - `assigned_rm` → Link to RE Relationship Manager

### 5.2 Doctype: `RE Booking` (Core Transaction Doctype)

This is the central document. Created when a customer confirms and pays booking amount.

|Field                       |Type                          |Notes                                                                        |
|----------------------------|------------------------------|-----------------------------------------------------------------------------|
|booking_number              |Data                          |Auto-named: BK-YYYY-XXXXX                                                    |
|booking_date                |Date                          |Required                                                                     |
|project                     |Link → RE Project             |Required                                                                     |
|plot                        |Link → RE Plot                |Required, only Available plots selectable                                    |
|customer                    |Link → Customer               |ERPNext native Customer                                                      |
|assigned_rm                 |Link → RE Relationship Manager|Required                                                                     |
|payment_plan_type           |Select                        |Down Payment Plan / Development Linked Plan                                  |
|plot_value                  |Currency                      |Fetched from plot, editable if negotiated                                    |
|discount                    |Currency                      |Optional                                                                     |
|final_value                 |Currency                      |plot_value − discount                                                        |
|possession_date             |Date                          |Expected possession, drives final payment due date                           |
|booking_status              |Select                        |Draft / Booked / Payment In Progress / Possession Due / Completed / Cancelled|
|notes                       |Text Editor                   |                                                                             |
|**Payment Schedule Section**|                              |Child table — auto-generated                                                 |
|**Document Cabinet Section**|                              |Child table                                                                  |

**On Submit:**

- Plot status automatically changes to `Booked`.
- Payment schedule is auto-generated based on selected plan type (see Module 4).
- A GL entry is created for the booking amount received (if booking amount payment is recorded).

**On Cancel:**

- Plot status reverts to `Available`.
- All pending payment schedule entries are cancelled.

-----

## 6. Module 3 — Relationship Manager (RM) Master

### 6.1 Doctype: `RE Relationship Manager`

|Field            |Type                          |Notes                                        |
|-----------------|------------------------------|---------------------------------------------|
|rm_name          |Data                          |Full name, Required                          |
|rm_code          |Data                          |Auto or manual short code                    |
|employee         |Link → Employee               |Optional — link to ERPNext Employee if exists|
|mobile           |Data                          |                                             |
|email            |Data                          |                                             |
|designation      |Data                          |e.g., Sales Executive, Senior RM             |
|joining_date     |Date                          |                                             |
|status           |Select                        |Active / Inactive                            |
|assigned_projects|Table Multiselect → RE Project|Projects this RM handles                     |
|profile_photo    |Attach Image                  |                                             |
|notes            |Text                          |                                             |

**List View** must show: Name, Code, Mobile, Status, Active Bookings count (computed).

**Permissions:**

- Only HR Manager or System Manager can Add / Edit / Delete RMs.
- Sales users can only view.

**RM Dashboard (within doctype):**

- Total leads assigned
- Total bookings closed
- Total revenue generated (sum of final_value of their bookings)
- List of their current active bookings

-----

## 7. Module 4 — Payment Plan Engine

### 7.1 Payment Plan Rules (Hardcoded as configurable masters)

Create a doctype `RE Payment Plan Template` so plans can be managed without code changes.

#### Doctype: `RE Payment Plan Template`

|Field      |Type                               |Notes                    |
|-----------|-----------------------------------|-------------------------|
|plan_name  |Data                               |e.g., “Down Payment Plan”|
|plan_code  |Data                               |DOWN / DEV_LINKED        |
|description|Text                               |                         |
|stages     |Child Table → RE Payment Plan Stage|                         |

#### Child Doctype: `RE Payment Plan Stage`

|Field              |Type  |Notes                                                                |
|-------------------|------|---------------------------------------------------------------------|
|stage_name         |Data  |e.g., “Booking Amount”, “30-Day Installment”                         |
|stage_order        |Int   |1, 2, 3…                                                             |
|percentage         |Float |% of final plot value                                                |
|due_trigger        |Select|On Booking / Days from Booking / Days from Possession / On Possession|
|due_days           |Int   |Used when trigger is “Days from Booking” or “Days from Possession”   |
|is_possession_stage|Check |If checked, due date = possession date                               |

#### Pre-configured Plan A: Down Payment Plan

|Stage             |%  |Trigger             |
|------------------|---|--------------------|
|Booking Amount    |10%|On Booking          |
|30-Day Payment    |80%|30 days from Booking|
|Possession Payment|10%|On Possession       |

#### Pre-configured Plan B: Development Linked Plan

|Stage              |%  |Trigger              |
|-------------------|---|---------------------|
|Booking Amount     |10%|On Booking           |
|60-Day Installment |30%|60 days from Booking |
|120-Day Installment|30%|120 days from Booking|
|270-Day Installment|20%|270 days from Booking|
|Possession Payment |20%|On Possession        |


> **Note:** Percentages are cumulative as communicated by client. Above table shows per-stage incremental percentages. Ensure total = 100%. Clarify with client on Plan B possession stage (client said 10%, math suggests 20% — build it as configurable so it can be corrected).

### 7.2 Child Doctype: `RE Booking Payment Schedule`

Auto-generated inside RE Booking on submit.

|Field          |Type                |Notes                             |
|---------------|--------------------|----------------------------------|
|stage_name     |Data                |From template                     |
|stage_order    |Int                 |                                  |
|percentage     |Float               |                                  |
|amount_due     |Currency            |Calculated: % × final_value       |
|due_date       |Date                |Calculated from trigger rules     |
|amount_received|Currency            |Updated as payments come in       |
|balance        |Currency            |amount_due − amount_received      |
|status         |Select              |Pending / Partial / Paid / Overdue|
|payment_entry  |Link → Payment Entry|ERPNext native PE linked here     |
|receipt_date   |Date                |Actual receipt date               |

### 7.3 Payment Receipt Flow

- A custom button **“Receive Payment”** on RE Booking opens a dialog:
  - Select which schedule stage is being paid
  - Enter amount received
  - Enter payment date
  - Select payment mode (Cash / Cheque / Bank Transfer / UPI)
  - Enter reference number
- On confirmation:
  - Creates an ERPNext native **Payment Entry** linked to the customer
  - Updates `amount_received`, `balance`, `status` in the schedule row
  - Posts to GL automatically via ERPNext’s Payment Entry mechanism
  - If fully paid: marks stage as `Paid`
  - If overdue (today > due_date and not fully paid): stage marked `Overdue`

### 7.4 Overdue Alerts

- A scheduled job (daily) checks all booking payment schedules.
- If `due_date` has passed and `status` is not `Paid`, set status to `Overdue`.
- Send email notification to assigned RM and their manager.

-----

## 8. Module 5 — Document Cabinet

### 8.1 Purpose

Each booking (and customer) needs a structured, categorized document store — not just raw file attachments. Users must be able to click a document category and immediately open/preview the file.

### 8.2 Doctype: `RE Document Type` (Master)

Simple master list of document categories. Pre-populate on install.

Examples: Application Form, ID Proof, Address Proof, Booking Agreement, Payment Receipt, Sale Deed, NOC, Power of Attorney, Plot Map, Other

|Field             |Type                              |
|------------------|----------------------------------|
|document_type_name|Data                              |
|is_mandatory      |Check                             |
|applicable_to     |Select — Customer / Booking / Both|

### 8.3 Child Doctype: `RE Document Entry`

Used as a child table inside both **Customer** (custom fields section) and **RE Booking**.

|Field        |Type                   |Notes                            |
|-------------|-----------------------|---------------------------------|
|document_type|Link → RE Document Type|                                 |
|document_name|Data                   |Description e.g. “Aadhar Card”   |
|file         |Attach                 |Frappe file attach field         |
|uploaded_on  |Date                   |Auto set                         |
|uploaded_by  |Link → User            |Auto set                         |
|remarks      |Data                   |                                 |
|expiry_date  |Date                   |Optional — for docs with validity|

### 8.4 UI Behavior

- On the Booking form and Customer form, the Document Cabinet section shows the child table.
- Each row with an attached file must show a **“View”** button that opens the file in a new tab or inline preview (PDF viewer for PDFs, image viewer for images).
- Filter/group by document_type for easy navigation.
- Show a document checklist — highlight mandatory documents that are missing.

-----

## 9. Module 6 — Customer 360 Dashboard

### 9.1 Custom Page: `Customer 360`

Accessible from the Customer record via a button **“View 360°”**. This is a custom Frappe page or Dashboard that shows everything about a customer in one screen.

**Sections to display:**

1. **Customer Info** — Name, contact, address, assigned RM
1. **Bookings** — Table of all bookings (plot number, project, plan type, booking date, status)
1. **Payment Summary** — For each booking: total due, total received, total outstanding, next due date and amount
1. **Overdue Alerts** — Highlighted list of overdue payment stages
1. **Document Cabinet** — All documents across all bookings in one place, grouped by type, with View buttons
1. **Activity Log** — ERPNext’s native Communication/Comment log for the customer

### 9.2 Quick Actions from Dashboard

- Add new document
- Record payment (opens payment dialog)
- Send payment reminder (email)
- View booking detail

-----

## 10. Module 7 — Accounting Integration

### 10.1 Chart of Accounts (Setup)

On app install, create the following accounts under the company’s COA (if not already present):

- `Real Estate Revenue` (Income)
  - `Plot Sales Revenue`
- `Customer Advances` (Liability — for booking amounts before invoice)
- `Accounts Receivable — Real Estate` (Asset)

### 10.2 Posting Logic

|Event                                      |ERPNext Entry                                                                              |
|-------------------------------------------|-------------------------------------------------------------------------------------------|
|Booking confirmed + booking amount received|Payment Entry (advance) → debit Bank, credit Customer Advances                             |
|Payment schedule installment received      |Payment Entry → debit Bank, credit Accounts Receivable                                     |
|Final possession / Sale Deed               |Sales Invoice → recognize revenue (debit AR, credit Plot Sales Revenue), reconcile advances|
|Cancellation                               |Journal Entry to reverse                                                                   |

### 10.3 Sales Invoice Generation

- A button **“Generate Invoice”** on RE Booking (visible to Accounts role only).
- Creates a native ERPNext Sales Invoice linked to the customer.
- Line item: Plot Number — Plot Value.
- Advances already paid are auto-fetched and reconciled in the invoice.

-----

## 11. Module 8 — Reports

Build the following reports as ERPNext Script Reports or Query Reports:

### 11.1 Plot Inventory Status

- All plots, their status, value, booking date (if booked), customer name, RM name.
- Filter by: Project, Status, Facing, Sector.

### 11.2 Booking Register

- All bookings with: Booking No, Date, Customer, Plot, Plan Type, Final Value, RM, Status.
- Filter by: Project, RM, Date Range, Status.

### 11.3 Payment Collection Report

- Per booking: each stage, amount due, amount received, balance, due date, receipt date, status.
- Filter by: Project, RM, Date Range, Overdue only.
- Summary row: Total due, total collected, total outstanding.

### 11.4 RM Performance Report

- Per RM: Leads assigned, Opportunities, Bookings closed, Revenue generated, Outstanding collection.

### 11.5 Overdue Payment Report

- All stages where status = Overdue.
- Grouped by RM for accountability.
- Export to Excel.

### 11.6 Customer Ledger

- Per customer: all payment entries, amounts, dates, balance.
- Essentially a customer statement — can be emailed directly to customer.

-----

## 12. Roles & Permissions

|Role              |Access                                                                   |
|------------------|-------------------------------------------------------------------------|
|RE Admin          |Full access to all RE doctypes, settings                                 |
|RE Sales Manager  |View all bookings, all RMs, all reports. Cannot delete.                  |
|RE Sales Executive|Create/edit own leads and opportunities. View assigned bookings.         |
|RE Accounts       |Payment receipt, invoice generation, accounting reports                  |
|RE RM             |View own leads, bookings, payment schedules. Cannot edit booking details.|
|System Manager    |Full access                                                              |

Configure all permissions in the custom app’s `fixtures` so they install automatically.

-----

## 13. Workspace & Navigation

Create a custom **Workspace** called `Real Estate` with the following shortcuts:

- RE Project
- RE Plot (with status filter — Available Plots)
- RE Booking
- RE Relationship Manager
- Customer (filtered to RE customers)
- Payment Collection Report
- Plot Inventory Status
- Overdue Payment Report
- RE Payment Plan Template

-----

## 14. Installation & Setup

### 14.1 App Structure

```
real_estate_crm/
├── real_estate_crm/
│   ├── doctype/
│   │   ├── re_project/
│   │   ├── re_plot/
│   │   ├── re_booking/
│   │   ├── re_relationship_manager/
│   │   ├── re_payment_plan_template/
│   │   ├── re_payment_plan_stage/
│   │   ├── re_booking_payment_schedule/
│   │   ├── re_document_type/
│   │   └── re_document_entry/
│   ├── report/
│   ├── page/
│   │   └── customer_360/
│   ├── workspace/
│   ├── fixtures/
│   │   ├── roles.json
│   │   ├── re_document_type.json   ← pre-seeded document types
│   │   └── re_payment_plan_template.json  ← pre-seeded plans
│   └── hooks.py
├── setup.py
└── requirements.txt
```

### 14.2 On Install (via `after_install` hook)

- Create default document types
- Create Down Payment Plan and Development Linked Plan templates
- Create custom fields on Lead, Opportunity, Customer
- Create RE Workspace
- Create Chart of Accounts entries
- Assign default roles

-----

## 15. Tech Stack & Constraints

- **Framework:** Frappe v15 / ERPNext v15 (confirm version with client’s server)
- **Language:** Python (backend), JavaScript (frontend controllers)
- **Database:** MariaDB (standard ERPNext)
- **File Storage:** Frappe’s native file system (local or S3 if configured)
- **Email:** Frappe’s email queue for notifications
- **No external dependencies** beyond standard Frappe/ERPNext

-----

## 16. Out of Scope (for this version)

- Customer portal / login for customers to view their own payment status
- Mobile app
- WhatsApp integration for payment reminders
- Site map / plot layout visualizer
- Construction progress tracking
- Broker/channel partner management
- Loan / home finance integration

These can be Phase 2 items.

-----

## 17. Open Questions (Resolve Before Build)

1. **ERPNext version** running on client’s server — v14 or v15?
1. **Development Linked Plan possession stage** — is it 10% or 20%? Total must equal 100%.
1. **GST applicability** — do invoices need GST (under JDA or outright sale)?
1. **Existing data** — is there any data to migrate (customers, bookings) or is this a fresh start?
1. **Company name and base currency** — for COA setup during install.

-----

*Document Version: 1.0 | Prepared for: Claude Code | Project: Real Estate CRM on ERPNext*