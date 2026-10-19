"""
Performance benchmark for the evaluation chapter.

	bench --site <site> execute compliance_tracker.benchmark.run --kwargs "{'customers': 200}"

Creates N customers x 6 statutory services, then times:
  1. onboarding  - generating every obligation within the horizon for all N customers
  2. daily run   - refreshing every traffic light + the reminder decision for every open obligation,
                   on a normal day (everything already due has been filed)
  3. re-run      - generation again; must create 0 (idempotency)

Everything is ROLLED BACK at the end: the database is left exactly as it was.
"""

import time

import frappe
from frappe.utils import add_months, get_first_day, today

from compliance_tracker.generation import generate_for_customer
from compliance_tracker.scheduler import refresh_statuses, send_reminders
from compliance_tracker.settings import get_settings

SERVICES = ["VAT", "APIT", "SSCL", "EPF", "Bookkeeping", "Income Tax Return"]


def timed(fn, *args):
	start = time.perf_counter()
	result = fn(*args)
	return result, round(time.perf_counter() - start, 2)


def run(customers=200):
	customers = int(customers)
	settings = get_settings()
	frappe.flags.mute_emails = True
	result = {"customers": customers, "services_per_customer": len(SERVICES)}
	try:
		names, result["setup_seconds"] = timed(make_customers, customers)

		result["obligations_created"], result["generation_seconds"] = timed(generate_all, names, settings)
		result["ms_per_obligation"] = round(
			1000 * result["generation_seconds"] / max(1, result["obligations_created"]), 1
		)

		# a normal working day: everything already due has been filed on time
		frappe.db.sql(
			"""update `tabTask` set status='Completed', completed_on=date(exp_end_date),
			custom_compliance_status='Completed On Time'
			where custom_customer like 'Benchmark Customer %%' and exp_end_date < %s""",
			today(),
		)
		result["statuses_updated"], result["refresh_seconds"] = timed(refresh_statuses, settings)
		result["reminders_sent"], result["reminder_seconds"] = timed(send_reminders, settings)
		result["daily_run_seconds"] = round(result["refresh_seconds"] + result["reminder_seconds"], 2)

		result["rerun_created"], result["rerun_seconds"] = timed(generate_all, names, settings)
	finally:
		frappe.db.rollback()
		frappe.flags.mute_emails = False

	for key, value in result.items():
		print(f"{key:24} {value}")
	return result


def generate_all(names, settings):
	return sum(generate_for_customer(name, settings) for name in names)


def make_customers(count):
	monthly_start = get_first_day(add_months(today(), -2))
	annual_start = get_first_day(add_months(today(), -12))
	names = []
	for i in range(1, count + 1):
		customer = frappe.get_doc(
			{"doctype": "Customer", "customer_name": f"Benchmark Customer {i:04d}", "customer_type": "Company"}
		)
		for service in SERVICES:
			item = frappe.get_cached_doc("Item", service)
			annual = item.custom_filing_frequency == "Annual"
			customer.append(
				"custom_compliance_services",
				{
					"service": service,
					"frequency": item.custom_filing_frequency,
					"due_day": item.custom_due_day,
					"months_after_period_end": item.custom_months_after_period_end,
					"start_date": annual_start if annual else monthly_start,
					"active": 1,
				},
			)
		customer.insert(ignore_permissions=True)
		frappe.db.set_value("Customer", customer.name, "email_id", f"bench{i}@example.com")
		names.append(customer.name)
	return names
