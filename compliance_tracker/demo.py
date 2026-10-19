"""
Demo data for presentations and screenshots: five Sri Lankan clients with a realistic filing history.

	bench --site <site> execute compliance_tracker.demo.create_demo_data

Safe to run more than once: customers and users that already exist are left as they are.
No reminders are sent here (the demo clients use example.com addresses); reminders are the scheduler's job.
"""

import random

import frappe
from frappe.utils import add_days, add_months, get_first_day, getdate, today
from frappe.utils.password import update_password

from compliance_tracker.generation import generate_for_customer
from compliance_tracker.scheduler import refresh_statuses
from compliance_tracker.settings import get_settings

PASSWORD = "Demo@2026"

USERS = {
	# e-mail: (first name, roles)
	"manager@vtas.lk": ("Manager", ["Compliance Manager", "Projects Manager", "Sales Manager"]),
	"staff@vtas.lk": ("Staff", ["Compliance Staff", "Projects User", "Sales User"]),
	"nadeesha@vtas.lk": ("Nadeesha", ["Compliance Staff", "Projects User", "Sales User"]),
}

CUSTOMERS = [
	# customer name, statutory services, responsible staff
	("Lanka Spice Exporters (Pvt) Ltd", ["VAT", "APIT", "SSCL", "EPF", "ETF"], "staff@vtas.lk"),
	("Colombo Tech Solutions (Pvt) Ltd", ["VAT", "APIT", "EPF", "ETF", "Income Tax Return"], "nadeesha@vtas.lk"),
	("Kandy Hardware Stores", ["VAT", "Bookkeeping"], "staff@vtas.lk"),
	("Galle Boutique Hotels (Pvt) Ltd", ["VAT", "APIT", "SSCL", "ROC Annual Return"], "nadeesha@vtas.lk"),
	("Negombo Fisheries Co-operative", ["APIT", "EPF", "ETF", "Bookkeeping"], "staff@vtas.lk"),
]

DELAY_REASONS = {
	"Client": "Client sent the documents late",
	"Firm": "Staff on leave during the filing week",
	"Third Party": "IRD e-filing portal was unavailable",
}
DELAY_PARTIES = ["Client", "Client", "Client", "Firm", "Third Party"]  # clients cause most delays
REFERENCE_PREFIX = {"EPF": "EPF", "ETF": "ETF", "ROC Annual Return": "ROC"}


def create_demo_data():
	rng = random.Random(42)  # the same "random" history on every site
	for email, (first_name, roles) in USERS.items():
		make_user(email, first_name, roles)

	new_customers = []
	obligations = 0
	for name, services, staff in CUSTOMERS:
		if frappe.db.exists("Customer", name):
			continue
		make_customer(name, services, staff, rng)
		obligations += generate_for_customer(name)
		new_customers.append(name)

	filed = file_past_obligations(new_customers, rng)
	refresh_statuses(get_settings())
	frappe.db.commit()

	summary = (
		f"Demo data: {len(new_customers)} new customer(s), {obligations} obligation(s) generated, "
		f"{filed} past obligation(s) filed. Users' password: {PASSWORD}"
	)
	print(summary)
	return summary


def make_user(email, first_name, roles):
	if frappe.db.exists("User", email):
		return
	user = frappe.get_doc({"doctype": "User", "email": email, "first_name": first_name, "send_welcome_email": 0})
	for role in roles:
		user.append("roles", {"role": role})
	user.insert(ignore_permissions=True)
	update_password(email, PASSWORD)


def make_customer(name, services, staff, rng):
	monthly_start = get_first_day(add_months(today(), -4))
	annual_start = get_first_day(add_months(today(), -12))  # so last year's annual returns are included
	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": name,
			"customer_type": "Company",
			"tax_id": str(rng.randint(100000000, 999999999)),
		}
	)
	for service in services:
		item = frappe.get_cached_doc("Item", service)
		customer.append(
			"custom_compliance_services",
			{
				"service": service,
				"frequency": item.custom_filing_frequency,
				"due_day": item.custom_due_day,
				"months_after_period_end": item.custom_months_after_period_end,
				"start_date": annual_start if item.custom_filing_frequency == "Annual" else monthly_start,
				"responsible_staff": staff,
				"active": 1,
			},
		)
	customer.insert(ignore_permissions=True)

	# standard ERPNext Contact as the client's primary contact (fills Customer e-mail and mobile)
	short_name = name.split(" (")[0]
	contact = frappe.get_doc(
		{
			"doctype": "Contact",
			"first_name": "Accounts",
			"last_name": short_name,
			"email_ids": [{"email_id": f"{frappe.scrub(short_name)}@example.com", "is_primary": 1}],
			"phone_nos": [{"phone": f"077{rng.randint(1000000, 9999999)}", "is_primary_mobile_no": 1}],
			"links": [{"link_doctype": "Customer", "link_name": customer.name}],
		}
	).insert(ignore_permissions=True)
	customer.reload()
	customer.customer_primary_contact = contact.name
	customer.save(ignore_permissions=True)


def file_past_obligations(customers, rng):
	"""Mark most past-due obligations as filed: mostly on time, some late (with a reason), a few left overdue."""
	if not customers:
		return 0
	tasks = frappe.get_all(
		"Task",
		filters={"custom_customer": ("in", customers), "exp_end_date": ("<", today())},
		fields=["name"],
		order_by="exp_end_date asc",
	)
	filed = 0
	for t in tasks:
		roll = rng.random()
		if roll < 0.1:
			continue  # about 10% stay unfiled, so the demo shows red Overdue obligations

		task = frappe.get_doc("Task", t.name)
		due = getdate(task.exp_end_date)
		if roll < 0.3:  # about 20% filed late, with who caused it
			party = rng.choice(DELAY_PARTIES)
			task.completed_on = min(add_days(due, rng.randint(2, 9)), getdate(today()))
			task.custom_delay_responsibility = party
			task.custom_delay_reason = DELAY_REASONS[party]
		else:
			task.completed_on = add_days(due, -rng.randint(0, 6))
		task.status = "Completed"
		task.completed_by = (frappe.parse_json(task._assign or "[]") or [None])[0]
		task.custom_filing_reference = f"{REFERENCE_PREFIX.get(task.custom_service, 'IRD')}-{rng.randint(100000, 999999)}"
		task.save(ignore_permissions=True)
		filed += 1
	return filed
