import frappe
from frappe import _
from frappe.utils import getdate, today

from compliance_tracker.engine import status as S
from compliance_tracker.settings import get_settings


def validate(doc, method=None):
	if not is_obligation(doc):
		return  # an ordinary project task: leave it to ERPNext
	validate_required(doc)
	validate_duplicate(doc)
	set_due_end_of_day(doc)
	set_compliance_status(doc)
	validate_delay_accountability(doc)


def is_obligation(doc):
	"""A Task is a compliance obligation when it belongs to a customer's statutory service."""
	return bool(doc.custom_customer and doc.custom_service)


def validate_required(doc):
	if not doc.exp_end_date:
		frappe.throw(_("Expected End Date (the statutory due date) is required for a compliance obligation."))
	if not doc.custom_period_start:
		frappe.throw(_("Period Start is required for a compliance obligation."))


def validate_duplicate(doc):
	"""One obligation per customer, service and period (cancelled ones do not count)."""
	existing = frappe.db.exists(
		"Task",
		{
			"custom_customer": doc.custom_customer,
			"custom_service": doc.custom_service,
			"custom_period_start": doc.custom_period_start,
			"status": ("!=", "Cancelled"),
			"name": ("!=", doc.name),
		},
	)
	if existing:
		frappe.throw(
			_("{0} for {1} ({2}) already exists: {3}").format(
				doc.custom_service, doc.custom_customer, doc.custom_period or doc.custom_period_start, existing
			)
		)


def set_due_end_of_day(doc):
	# ERPNext marks a Task Overdue once exp_end_date has passed, so keep the whole due day available
	doc.exp_end_date = f"{getdate(doc.exp_end_date)} 23:59:59"


def set_compliance_status(doc):
	if doc.status == "Cancelled":
		doc.custom_compliance_status = None
		return
	filed_on = getdate(doc.completed_on) if doc.status == "Completed" and doc.completed_on else None
	doc.custom_compliance_status = S.classify(
		getdate(doc.exp_end_date), getdate(today()), filed_on, get_settings().at_risk_days
	)


def validate_delay_accountability(doc):
	"""A late filing cannot be saved without recording who caused the delay and why."""
	if doc.custom_compliance_status != S.COMPLETED_LATE:
		return
	if not doc.custom_delay_responsibility or not doc.custom_delay_reason:
		frappe.throw(
			_("Filed on {0}, after the due date {1}. Please set Delay Responsibility and Delay Reason.").format(
				frappe.format(doc.completed_on, "Date"), frappe.format(getdate(doc.exp_end_date), "Date")
			),
			title=_("Delay Accountability Required"),
		)
