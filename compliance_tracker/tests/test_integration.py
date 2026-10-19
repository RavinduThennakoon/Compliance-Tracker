"""
Integration tests: the app working with the real database (Customer, Task, Communication).

	bench --site <site> run-tests --module compliance_tracker.tests.test_integration

Dates are relative to today, so the tests keep working on any day.
IntegrationTestCase rolls the database back afterwards, so nothing they create is kept.
"""

import frappe
from frappe.desk.form.assign_to import add as add_assignment
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, add_months, get_first_day, getdate, today

from compliance_tracker.engine import recurrence as R
from compliance_tracker.generation import generate_for_customer
from compliance_tracker.notifications import ESCALATION, remind
from compliance_tracker.scheduler import refresh_statuses
from compliance_tracker.settings import get_settings
from compliance_tracker.www import my_compliance

STAFF = "_test.ct.staff@example.com"
MANAGER = "_test.ct.manager@example.com"
CLIENT_USER = "_test.ct.client@example.com"


def make_user(email, roles):
	if not frappe.db.exists("User", email):
		user = frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}
		)
		for role in roles:
			user.append("roles", {"role": role})
		user.insert(ignore_permissions=True)
	return email


def make_customer(name, services, start_date=None):
	"""A Customer with compliance services, plus the e-mail and mobile that reminders need."""
	customer = frappe.get_doc({"doctype": "Customer", "customer_name": name, "customer_type": "Company"})
	for service in services:
		item = frappe.get_cached_doc("Item", service)
		customer.append(
			"custom_compliance_services",
			{
				"service": service,
				"frequency": item.custom_filing_frequency,
				"due_day": item.custom_due_day,
				"months_after_period_end": item.custom_months_after_period_end,
				"start_date": start_date or get_first_day(add_months(today(), -2)),
				"responsible_staff": STAFF,
				"active": 1,
			},
		)
	customer.insert(ignore_permissions=True)
	frappe.db.set_value("Customer", customer.name, {"email_id": "client@example.com", "mobile_no": "0770000000"})
	return customer


def make_obligation(customer, service, due_date, period_start, assign=True):
	"""One obligation Task, as the generator creates it, with a due date relative to today."""
	task = frappe.get_doc(
		{
			"doctype": "Task",
			"subject": f"{service} test obligation",
			"type": "Statutory Filing",
			"exp_end_date": due_date,
			"custom_customer": customer,
			"custom_service": service,
			"custom_period": "Test period",
			"custom_period_start": period_start,
			"custom_period_end": add_days(period_start, 27),
		}
	).insert(ignore_permissions=True)
	if assign:
		add_assignment(
			{"assign_to": [STAFF], "doctype": "Task", "name": task.name, "description": task.subject},
			ignore_permissions=True,
		)
		task.reload()
	return task


def tiers_logged(task_name):
	return frappe.get_all(
		"Communication",
		filters={"reference_doctype": "Task", "reference_name": task_name},
		fields=["communication_medium", "custom_reminder_tier", "recipients"],
	)


class TestComplianceTracker(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_user(STAFF, ["Compliance Staff", "Projects User"])
		make_user(MANAGER, ["Compliance Manager", "Projects Manager"])
		cls.customer = make_customer("_Test CT Customer", ["VAT", "APIT"]).name

	# IT-01: obligations are generated from the customer's services, exactly as the engine computes them
	def test_generation_matches_engine_and_is_idempotent(self):
		customer = make_customer("_Test CT Generation", ["VAT"])
		row = customer.custom_compliance_services[0]
		horizon = getdate(add_days(today(), get_settings().generation_horizon_days))
		expected = R.generate_periods(row.frequency, getdate(row.start_date), horizon, row.due_day, 1)

		created = generate_for_customer(customer.name)
		self.assertEqual(created, len(expected))
		self.assertGreater(created, 0)

		tasks = frappe.get_all(
			"Task",
			filters={"custom_customer": customer.name},
			fields=["exp_end_date", "type", "_assign", "custom_compliance_status"],
			order_by="exp_end_date asc",
		)
		self.assertEqual([getdate(t.exp_end_date) for t in tasks], [p.due_date for p in expected])
		for t in tasks:
			self.assertEqual(t.type, "Statutory Filing")
			self.assertIn(STAFF, frappe.parse_json(t._assign))
			self.assertTrue(t.custom_compliance_status)

		self.assertEqual(generate_for_customer(customer.name), 0)  # second run creates nothing

	# IT-02: a cancelled obligation is not re-created by the next run
	def test_cancelled_obligation_is_not_recreated(self):
		customer = make_customer("_Test CT Cancel", ["APIT"])
		generate_for_customer(customer.name)
		first = frappe.get_all("Task", filters={"custom_customer": customer.name}, pluck="name", limit=1)[0]
		task = frappe.get_doc("Task", first)
		task.status = "Cancelled"
		task.save()
		self.assertEqual(generate_for_customer(customer.name), 0)

	# IT-03: the same customer + service + period cannot be entered twice
	def test_duplicate_obligation_is_blocked(self):
		make_obligation(self.customer, "VAT", add_days(today(), 30), "2020-01-01", assign=False)
		with self.assertRaises(frappe.ValidationError):
			make_obligation(self.customer, "VAT", add_days(today(), 30), "2020-01-01", assign=False)

	# IT-04: traffic light on save, and the daily refresh corrects a stale status
	def test_traffic_light_and_daily_refresh(self):
		task = make_obligation(self.customer, "VAT", add_days(today(), 2), "2020-02-01", assign=False)
		self.assertEqual(task.custom_compliance_status, "At Risk")
		self.assertEqual(str(task.exp_end_date)[11:], "23:59:59")

		frappe.db.set_value("Task", task.name, "custom_compliance_status", "On Track")
		refresh_statuses(get_settings())
		self.assertEqual(frappe.db.get_value("Task", task.name, "custom_compliance_status"), "At Risk")

	# IT-05: a late filing cannot be saved without delay responsibility and reason
	def test_late_filing_requires_delay_accountability(self):
		task = make_obligation(self.customer, "APIT", add_days(today(), -5), "2020-03-01", assign=False)
		task.status = "Completed"
		task.completed_on = today()
		with self.assertRaises(frappe.ValidationError):
			task.save()

		task = frappe.get_doc("Task", task.name)
		task.status = "Completed"
		task.completed_on = today()
		task.custom_delay_responsibility = "Client"
		task.custom_delay_reason = "Invoices received late"
		task.save()
		self.assertEqual(task.custom_compliance_status, "Completed Late")

	# IT-06: tiered reminder to client and staff, logged with its tier, never sent twice
	def test_tiered_reminder_is_logged_and_not_duplicated(self):
		task = make_obligation(self.customer, "VAT", add_days(today(), 10), "2020-04-01")
		self.assertEqual(remind(task, get_settings()), "10-Day Reminder")

		logged = tiers_logged(task.name)
		self.assertEqual(len(logged), 2)  # client e-mail + staff e-mail
		self.assertEqual({c.custom_reminder_tier for c in logged}, {"10-Day Reminder"})
		self.assertTrue(any(STAFF in c.recipients for c in logged))

		self.assertIsNone(remind(task, get_settings()))
		self.assertEqual(len(tiers_logged(task.name)), 2)

	# IT-07: overdue escalation reaches the compliance manager
	def test_overdue_escalation_reaches_manager(self):
		task = make_obligation(self.customer, "APIT", add_days(today(), -1), "2020-05-01")
		self.assertEqual(remind(task, get_settings()), ESCALATION)
		staff_mail = [c for c in tiers_logged(task.name) if STAFF in c.recipients]
		self.assertTrue(staff_mail and MANAGER in staff_mail[0].recipients)

	# IT-08: SMS only for a critical service near the deadline, when SMS is enabled
	def test_sms_logged_for_critical_service(self):
		settings = get_settings()
		settings.enable_sms = 1
		task = make_obligation(self.customer, "VAT", add_days(today(), 2), "2020-06-01")  # VAT is critical
		self.assertEqual(remind(task, settings), "3-Day Reminder")
		sms = [c for c in tiers_logged(task.name) if c.communication_medium == "SMS"]
		self.assertEqual(len(sms), 1)
		self.assertEqual(sms[0].custom_reminder_tier, "3-Day Reminder")

	# IT-09: a portal user sees only the obligations of their own customer
	def test_portal_shows_only_own_customer(self):
		own = make_customer("_Test CT Portal Own", ["VAT"])
		other = make_customer("_Test CT Portal Other", ["VAT"])
		generate_for_customer(own.name)
		generate_for_customer(other.name)

		make_user(CLIENT_USER, [])
		own.reload()
		own.append("portal_users", {"user": CLIENT_USER})
		own.save()
		self.assertEqual(frappe.db.get_value("User", CLIENT_USER, "user_type"), "Website User")

		with self.set_user(CLIENT_USER):
			context = my_compliance.get_context(frappe._dict())
		shown = {o.name for o in context.pending + context.history}
		own_tasks = set(frappe.get_all("Task", filters={"custom_customer": own.name}, pluck="name"))
		self.assertEqual(context.customer.name, own.name)
		self.assertEqual(shown, own_tasks)
