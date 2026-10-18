"""Turn each Customer's compliance services into obligation Tasks, using the due-date engine."""

import frappe
from frappe.desk.form.assign_to import add as add_assignment
from frappe.utils import add_days, getdate, today

from compliance_tracker.engine import recurrence as R
from compliance_tracker.install import TASK_TYPE
from compliance_tracker.settings import get_settings

ALLOWED_ROLES = ("System Manager", "Compliance Manager", "Compliance Staff")


@frappe.whitelist()
def generate_now(customer):
	"""'Generate Obligations Now' button on the Customer form."""
	frappe.only_for(ALLOWED_ROLES)
	return generate_for_customer(customer)


def generate_for_all_customers(settings=None):
	settings = settings or get_settings()
	created = 0
	for name in frappe.get_all("Customer", filters={"disabled": 0}, pluck="name"):
		try:
			created += generate_for_customer(name, settings)
		except Exception:
			# one bad customer must not stop the daily run for everyone else
			frappe.log_error(title=f"Compliance: obligation generation failed for {name}")
	return created


def generate_for_customer(customer_name, settings=None):
	"""Create the missing obligations of one customer whose due date is within the horizon."""
	settings = settings or get_settings()
	customer = frappe.get_doc("Customer", customer_name)
	horizon = getdate(add_days(today(), settings.generation_horizon_days))
	created = 0
	for row in customer.get("custom_compliance_services") or []:
		if not row.active:
			continue
		periods = R.generate_periods(
			row.frequency,
			getdate(row.start_date),
			horizon,
			row.due_day or 0,
			row.months_after_period_end or 0,
			one_off_due_date=getdate(row.one_off_due_date) if row.one_off_due_date else None,
		)
		for period in periods:
			if not obligation_exists(customer.name, row.service, period.start):
				create_obligation(customer, row, period)
				created += 1
	return created


def obligation_exists(customer, service, period_start):
	# includes Cancelled tasks on purpose: a cancelled obligation must not be re-created every morning
	return frappe.db.exists(
		"Task", {"custom_customer": customer, "custom_service": service, "custom_period_start": period_start}
	)


def create_obligation(customer, row, period):
	critical = frappe.db.get_value("Item", row.service, "custom_critical_deadline")
	task = frappe.get_doc(
		{
			"doctype": "Task",
			"subject": f"{row.service} - {period.label} - {customer.customer_name}",
			"type": TASK_TYPE,
			"status": "Open",
			"priority": "High" if critical else "Medium",
			# work can start once the period has closed (a one-off has no period, so it starts on its due date)
			"exp_start_date": min(getdate(add_days(period.end, 1)), period.due_date),
			"exp_end_date": period.due_date,
			"company": frappe.defaults.get_global_default("company"),
			"custom_customer": customer.name,
			"custom_service": row.service,
			"custom_period": period.label,
			"custom_period_start": period.start,
			"custom_period_end": period.end,
		}
	).insert(ignore_permissions=True)

	if row.responsible_staff:
		add_assignment(
			{"assign_to": [row.responsible_staff], "doctype": "Task", "name": task.name, "description": task.subject},
			ignore_permissions=True,
		)
	return task
