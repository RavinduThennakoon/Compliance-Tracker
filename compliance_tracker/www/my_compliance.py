"""Client portal: /my-compliance

For website users linked to a Customer through the standard Customer > Portal Users table
(ERPNext gives them the standard "Customer" role). A client only ever sees the obligations
of the Customer their login is linked to.
"""

import frappe
from frappe import _
from frappe.utils import getdate, today

from erpnext.controllers.website_list_for_contact import get_parents_for_user

no_cache = 1

FIELDS = [
	"name",
	"custom_service",
	"custom_period",
	"exp_end_date",
	"status",
	"custom_compliance_status",
	"completed_on",
	"custom_filing_reference",
]


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/my-compliance"
		raise frappe.Redirect

	customers = get_parents_for_user("Customer")
	if not customers:
		frappe.throw(
			_("No client profile is linked to your login. Please contact your tax advisor."), frappe.PermissionError
		)

	customer = frappe.db.get_value(
		"Customer", customers[0], ["name", "customer_name", "customer_type", "tax_id"], as_dict=True
	)
	# get_all skips role permissions (a website user has none on Task),
	# so this customer filter is the security boundary: only this client's obligations are read
	obligations = frappe.get_all(
		"Task",
		filters={"custom_customer": customer.name, "status": ("!=", "Cancelled")},
		fields=FIELDS,
		order_by="exp_end_date asc",
	)

	advisories = dict(
		frappe.get_all(
			"Item",
			filters={"name": ("in", list({o.custom_service for o in obligations}) or [""])},
			fields=["name", "custom_penalty_advisory"],
			as_list=True,
		)
	)
	today_date = getdate(today())
	for o in obligations:
		o.due_date = getdate(o.exp_end_date)
		o.days_to_due = (o.due_date - today_date).days
		o.advisory = advisories.get(o.custom_service)

	pending = [o for o in obligations if o.status != "Completed"]
	history = sorted([o for o in obligations if o.status == "Completed"], key=lambda o: o.due_date, reverse=True)

	context.no_breadcrumbs = True
	context.show_sidebar = True
	context.title = _("My Compliance")
	context.customer = customer
	context.pending = pending
	context.history = history
	context.counts = {
		"pending": len(pending),
		"overdue": len([o for o in pending if o.custom_compliance_status == "Overdue"]),
		"at_risk": len([o for o in pending if o.custom_compliance_status == "At Risk"]),
		"filed": len(history),
	}
	return context
