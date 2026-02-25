frappe.pages["customer-360"].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Customer 360\u00b0",
        single_column: true,
    });

    page.main.addClass("customer-360-page");

    // --- Customer Selector ---
    let customer_field = page.add_field({
        label: "Customer",
        fieldtype: "Link",
        fieldname: "customer",
        options: "Customer",
        change: function () {
            let customer = customer_field.get_value();
            if (customer) {
                load_customer_data(page, customer);
            } else {
                page.$content.empty();
            }
        },
    });

    // Container for the 360 content
    $('<div class="customer-360-content"></div>').appendTo(page.main);
    page.$content = page.main.find(".customer-360-content");

    // Pick up customer from URL hash
    page.wrapper.on("show", function () {
        let customer = frappe.get_route()[1];
        if (customer) {
            customer_field.set_value(customer);
        }
    });
};

function load_customer_data(page, customer) {
    page.$content.empty();
    page.$content.html(
        '<div class="text-center" style="padding:60px 0;"><div class="spinner-border text-primary" role="status"></div><p class="text-muted mt-3">Loading customer data&hellip;</p></div>'
    );

    frappe.call({
        method: "real_estate_crm.real_estate_crm.page.customer_360.customer_360.get_customer_360_data",
        args: { customer: customer },
        callback: function (r) {
            if (r.message) {
                render_360(page, r.message, customer);
            }
        },
        error: function () {
            page.$content.html(
                '<div class="text-center text-muted" style="padding:60px 0;"><i class="fa fa-exclamation-triangle text-danger fa-2x"></i><p class="mt-3">Failed to load data.</p></div>'
            );
        },
    });
}

/* ------------------------------------------------------------------ */
/*  Master render                                                      */
/* ------------------------------------------------------------------ */
function render_360(page, data, customer) {
    page.$content.empty();

    // Quick action bar
    render_action_bar(page.$content, data, customer);

    // Customer info card
    render_customer_info(page.$content, data.customer_info);

    // Overdue alerts (render prominently if any)
    if (data.overdue_stages && data.overdue_stages.length) {
        render_overdue_alerts(page.$content, data.overdue_stages);
    }

    // Bookings + payment summary
    render_bookings(page.$content, data.bookings, data.payment_summary);

    // Document cabinet
    render_documents(page.$content, data.documents);

    // Activity log
    render_activity(page.$content, data.activity);
}

/* ------------------------------------------------------------------ */
/*  Quick Actions                                                      */
/* ------------------------------------------------------------------ */
function render_action_bar(container, data, customer) {
    let html = `
    <div class="frappe-card p-3 mb-4">
        <div class="d-flex flex-wrap gap-2" style="gap:8px;">
            <button class="btn btn-primary btn-sm btn-add-document">
                <i class="fa fa-plus"></i> Add Document
            </button>
            ${
                data.bookings && data.bookings.length
                    ? `<button class="btn btn-success btn-sm btn-record-payment">
                        <i class="fa fa-money"></i> Record Payment
                       </button>
                       <button class="btn btn-default btn-sm btn-view-booking">
                        <i class="fa fa-external-link"></i> View Booking
                       </button>`
                    : ""
            }
        </div>
    </div>`;

    let $bar = $(html).appendTo(container);

    $bar.find(".btn-add-document").on("click", function () {
        frappe.set_route("Form", "Customer", customer);
    });

    if (data.bookings && data.bookings.length) {
        let first_booking = data.bookings[0].name;

        $bar.find(".btn-record-payment").on("click", function () {
            if (data.bookings.length === 1) {
                frappe.set_route("Form", "RE Booking", first_booking);
            } else {
                show_booking_picker(data.bookings, function (b) {
                    frappe.set_route("Form", "RE Booking", b);
                });
            }
        });

        $bar.find(".btn-view-booking").on("click", function () {
            if (data.bookings.length === 1) {
                frappe.set_route("Form", "RE Booking", first_booking);
            } else {
                show_booking_picker(data.bookings, function (b) {
                    frappe.set_route("Form", "RE Booking", b);
                });
            }
        });
    }
}

function show_booking_picker(bookings, callback) {
    let options = bookings.map(
        (b) => `${b.name} - ${b.plot || ""} (${b.project || ""})`
    );
    let d = new frappe.ui.Dialog({
        title: __("Select Booking"),
        fields: [
            {
                fieldtype: "Select",
                fieldname: "booking",
                label: "Booking",
                options: options.join("\n"),
                reqd: 1,
            },
        ],
        primary_action_label: __("Go"),
        primary_action: function (values) {
            let booking_name = values.booking.split(" - ")[0];
            d.hide();
            callback(booking_name);
        },
    });
    d.show();
}

/* ------------------------------------------------------------------ */
/*  Customer Info                                                      */
/* ------------------------------------------------------------------ */
function render_customer_info(container, info) {
    let rm_display = info.rm_name
        ? `<a href="/app/re-relationship-manager/${encodeURIComponent(info.assigned_rm)}">${info.rm_name}</a>`
        : '<span class="text-muted">Not Assigned</span>';

    let html = `
    <div class="frappe-card p-4 mb-4">
        <h5 class="mb-3" style="font-weight:600;">
            <i class="fa fa-user-circle text-primary"></i> Customer Information
        </h5>
        <div class="row">
            <div class="col-md-6">
                <table class="table table-borderless table-sm mb-0">
                    <tr>
                        <td class="text-muted" style="width:140px;">Name</td>
                        <td class="font-weight-bold">
                            <a href="/app/customer/${encodeURIComponent(info.name)}">${info.customer_name || info.name}</a>
                        </td>
                    </tr>
                    <tr>
                        <td class="text-muted">Email</td>
                        <td>${info.email || '<span class="text-muted">-</span>'}</td>
                    </tr>
                    <tr>
                        <td class="text-muted">Mobile</td>
                        <td>${info.mobile || '<span class="text-muted">-</span>'}</td>
                    </tr>
                </table>
            </div>
            <div class="col-md-6">
                <table class="table table-borderless table-sm mb-0">
                    <tr>
                        <td class="text-muted" style="width:140px;">Address</td>
                        <td>${info.address || '<span class="text-muted">-</span>'}</td>
                    </tr>
                    <tr>
                        <td class="text-muted">Assigned RM</td>
                        <td>${rm_display}</td>
                    </tr>
                </table>
            </div>
        </div>
    </div>`;

    $(html).appendTo(container);
}

/* ------------------------------------------------------------------ */
/*  Overdue Alerts                                                     */
/* ------------------------------------------------------------------ */
function render_overdue_alerts(container, overdue) {
    let rows = overdue
        .map(
            (o) => `
        <tr style="background:#fff5f5;">
            <td>
                <a href="/app/re-booking/${encodeURIComponent(o.booking)}">${o.booking}</a>
            </td>
            <td>${o.stage_name || "-"}</td>
            <td>${frappe.datetime.str_to_user(o.due_date)}</td>
            <td class="text-right">${format_currency(o.amount)}</td>
            <td class="text-right">${format_currency(o.outstanding)}</td>
            <td class="text-center">
                <span class="indicator-pill red">${o.days_overdue} days</span>
            </td>
        </tr>`
        )
        .join("");

    let html = `
    <div class="frappe-card p-4 mb-4" style="border-left:4px solid var(--red-500, #e24c4c);">
        <h5 class="mb-3" style="font-weight:600; color:var(--red-500, #e24c4c);">
            <i class="fa fa-exclamation-triangle"></i> Overdue Payments
        </h5>
        <div class="table-responsive">
            <table class="table table-sm table-hover mb-0">
                <thead>
                    <tr class="text-muted" style="font-size:0.85em;">
                        <th>Booking</th>
                        <th>Stage</th>
                        <th>Due Date</th>
                        <th class="text-right">Amount</th>
                        <th class="text-right">Outstanding</th>
                        <th class="text-center">Overdue By</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
    </div>`;

    $(html).appendTo(container);
}

/* ------------------------------------------------------------------ */
/*  Bookings & Payment Summary                                         */
/* ------------------------------------------------------------------ */
function render_bookings(container, bookings, payment_summary) {
    if (!bookings || !bookings.length) {
        $(
            '<div class="frappe-card p-4 mb-4 text-center text-muted">No bookings found for this customer.</div>'
        ).appendTo(container);
        return;
    }

    let cards = bookings
        .map((b) => {
            let ps = payment_summary[b.name] || {};
            let status_color = get_status_color(b.booking_status);
            let next_due =
                ps.next_due_date
                    ? `${frappe.datetime.str_to_user(ps.next_due_date)} &mdash; ${format_currency(ps.next_due_amount)}`
                    : '<span class="text-muted">None</span>';

            return `
            <div class="frappe-card p-4 mb-3">
                <div class="d-flex justify-content-between align-items-start mb-3">
                    <div>
                        <h6 class="mb-1" style="font-weight:600;">
                            <a href="/app/re-booking/${encodeURIComponent(b.name)}">${b.name}</a>
                        </h6>
                        <span class="text-muted" style="font-size:0.85em;">
                            ${b.plot || ""} &bull; ${b.project || ""}
                        </span>
                    </div>
                    <span class="indicator-pill ${status_color}">${b.booking_status || "Draft"}</span>
                </div>

                <div class="row" style="font-size:0.9em;">
                    <div class="col-md-3 col-6 mb-2">
                        <div class="text-muted">Plan Type</div>
                        <div class="font-weight-bold">${b.payment_plan_type || "-"}</div>
                    </div>
                    <div class="col-md-3 col-6 mb-2">
                        <div class="text-muted">Booking Date</div>
                        <div class="font-weight-bold">${b.booking_date ? frappe.datetime.str_to_user(b.booking_date) : "-"}</div>
                    </div>
                    <div class="col-md-3 col-6 mb-2">
                        <div class="text-muted">Final Value</div>
                        <div class="font-weight-bold">${format_currency(b.final_value)}</div>
                    </div>
                    <div class="col-md-3 col-6 mb-2">
                        <div class="text-muted">Next Due</div>
                        <div class="font-weight-bold">${next_due}</div>
                    </div>
                </div>

                <hr class="my-2">

                <div class="row text-center" style="font-size:0.85em;">
                    <div class="col-4">
                        <div class="text-muted">Total Due</div>
                        <div class="font-weight-bold" style="font-size:1.1em;">${format_currency(ps.total_due)}</div>
                    </div>
                    <div class="col-4">
                        <div class="text-muted">Received</div>
                        <div class="font-weight-bold text-success" style="font-size:1.1em;">${format_currency(ps.total_received)}</div>
                    </div>
                    <div class="col-4">
                        <div class="text-muted">Outstanding</div>
                        <div class="font-weight-bold text-danger" style="font-size:1.1em;">${format_currency(ps.total_outstanding)}</div>
                    </div>
                </div>
            </div>`;
        })
        .join("");

    let html = `
    <div class="mb-4">
        <h5 class="mb-3" style="font-weight:600;">
            <i class="fa fa-bookmark text-primary"></i> Bookings (${bookings.length})
        </h5>
        ${cards}
    </div>`;

    $(html).appendTo(container);
}

/* ------------------------------------------------------------------ */
/*  Document Cabinet                                                   */
/* ------------------------------------------------------------------ */
function render_documents(container, documents) {
    let html;
    if (!documents || !documents.length) {
        html = `
        <div class="frappe-card p-4 mb-4">
            <h5 class="mb-3" style="font-weight:600;">
                <i class="fa fa-folder-open text-primary"></i> Document Cabinet
            </h5>
            <p class="text-muted text-center mb-0">No documents found.</p>
        </div>`;
    } else {
        // Group by document_type
        let grouped = {};
        documents.forEach((d) => {
            let dtype = d.document_type || "Other";
            if (!grouped[dtype]) grouped[dtype] = [];
            grouped[dtype].push(d);
        });

        let sections = Object.keys(grouped)
            .sort()
            .map((dtype) => {
                let items = grouped[dtype]
                    .map(
                        (d) => `
                    <div class="d-flex justify-content-between align-items-center py-2 px-3" style="border-bottom:1px solid var(--border-color, #eee);">
                        <div>
                            <span class="font-weight-bold">${d.document_name || dtype}</span>
                            <br>
                            <small class="text-muted">Source: ${d.source} &mdash; ${d.source_name}</small>
                        </div>
                        <div>
                            ${
                                d.file
                                    ? `<a href="${d.file}" target="_blank" class="btn btn-xs btn-default">
                                        <i class="fa fa-eye"></i> View
                                       </a>`
                                    : '<span class="text-muted">No file</span>'
                            }
                        </div>
                    </div>`
                    )
                    .join("");

                return `
                <div class="mb-3">
                    <div class="px-3 py-2" style="background:var(--bg-light-gray, #f7f7f7); font-weight:600; font-size:0.9em; border-radius:4px;">
                        ${dtype} (${grouped[dtype].length})
                    </div>
                    ${items}
                </div>`;
            })
            .join("");

        html = `
        <div class="frappe-card p-4 mb-4">
            <h5 class="mb-3" style="font-weight:600;">
                <i class="fa fa-folder-open text-primary"></i> Document Cabinet (${documents.length})
            </h5>
            ${sections}
        </div>`;
    }

    $(html).appendTo(container);
}

/* ------------------------------------------------------------------ */
/*  Activity Log                                                       */
/* ------------------------------------------------------------------ */
function render_activity(container, activity) {
    let html;
    if (!activity || !activity.length) {
        html = `
        <div class="frappe-card p-4 mb-4">
            <h5 class="mb-3" style="font-weight:600;">
                <i class="fa fa-clock-o text-primary"></i> Activity Log
            </h5>
            <p class="text-muted text-center mb-0">No recent activity.</p>
        </div>`;
    } else {
        let items = activity
            .map(
                (a) => `
            <div class="py-2 px-3" style="border-bottom:1px solid var(--border-color, #eee);">
                <div class="d-flex justify-content-between">
                    <span class="font-weight-bold" style="font-size:0.85em;">
                        ${a.comment_by || "System"}
                        ${a.source ? `<small class="text-muted ml-2">on ${a.source}</small>` : ""}
                    </span>
                    <small class="text-muted">${frappe.datetime.prettyDate(a.creation)}</small>
                </div>
                <div class="text-muted" style="font-size:0.85em;">${a.content || ""}</div>
            </div>`
            )
            .join("");

        html = `
        <div class="frappe-card p-4 mb-4">
            <h5 class="mb-3" style="font-weight:600;">
                <i class="fa fa-clock-o text-primary"></i> Activity Log
            </h5>
            ${items}
        </div>`;
    }

    $(html).appendTo(container);
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */
function format_currency(value) {
    if (value === undefined || value === null) return "-";
    return frappe.format(value, { fieldtype: "Currency" });
}

function get_status_color(status) {
    let map = {
        Draft: "gray",
        Booked: "blue",
        "Payment In Progress": "orange",
        "Possession Due": "yellow",
        Completed: "green",
        Cancelled: "red",
    };
    return map[status] || "gray";
}
