"""Daily compliance run: generate obligations, refresh the traffic lights, send reminders."""

import frappe
from frappe.utils import getdate, now_datetime, today

from compliance_tracker.engine import status as S
from compliance_tracker.generation import generate_for_all_customers
from compliance_tracker.notifications import remind
from compliance_tracker.settings import SETTINGS_DOCTYPE, get_settings

OPEN_OBLIGATIONS = {
	"custom_customer": ("is", "set"),
	"custom_service": ("is", "set"),
	"status": ("not in", ("Completed", "Cancelled")),
}


def run_daily():
	"""Called by the scheduler every day at 07:00 (hooks.py -> scheduler_events)."""
	settings = get_settings()
	created = generate_for_all_customers(settings)
	refreshed = refresh_statuses(settings)
	sent = send_reminders(settings)
	summary = (
		f"{now_datetime():%Y-%m-%d %H:%M}: created {created} obligation(s), "
		f"updated {refreshed} status(es), sent {sent} reminder(s)"
	)
	frappe.db.set_single_value(SETTINGS_DOCTYPE, "custom_last_run_summary", summary)
	frappe.db.commit()
	return summary


@frappe.whitelist()
def run_now():
	"""'Run Compliance Engine Now' button on Projects Settings."""
	frappe.only_for(("System Manager", "Compliance Manager"))
	return run_daily()


def refresh_statuses(settings):
	"""Recalculate the traffic light of every open obligation: days pass even when nobody edits a Task."""
	today_date = getdate(today())
	changed = 0
	for t in frappe.get_all(
		"Task", filters=OPEN_OBLIGATIONS, fields=["name", "exp_end_date", "custom_compliance_status"]
	):
		status = S.classify(getdate(t.exp_end_date), today_date, None, settings.at_risk_days)
		if status != t.custom_compliance_status:
			frappe.db.set_value("Task", t.name, "custom_compliance_status", status, update_modified=False)
			changed += 1
	return changed


def send_reminders(settings):
	sent = 0
	for name in frappe.get_all("Task", filters=OPEN_OBLIGATIONS, pluck="name"):
		try:
			if remind(frappe.get_doc("Task", name), settings):
				sent += 1
		except Exception:
			frappe.log_error(title=f"Compliance: reminder failed for {name}")
	return sent
