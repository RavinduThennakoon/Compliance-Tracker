"""Send compliance reminders by e-mail / SMS and log every message as a Communication on the Task."""

import frappe
from frappe.email.doctype.email_account.email_account import EmailAccount
from frappe.utils import format_date, get_url_to_form, getdate, today
from frappe.utils.user import get_users_with_role

from compliance_tracker.engine import reminder_rules as RR
from compliance_tracker.engine import status as S
from compliance_tracker.install import CLIENT_TEMPLATE, STAFF_TEMPLATE

ESCALATION = "Overdue Escalation"
MANAGER_ROLE = "Compliance Manager"


def remind(task, settings):
	"""Send today's reminder for one obligation, if the engine says one is due. Returns the tier sent, or None."""
	today_date = getdate(today())
	days_left = S.days_to_due(getdate(task.exp_end_date), today_date)
	customer = frappe.db.get_value("Customer", task.custom_customer, ["email_id", "mobile_no"], as_dict=True)
	staff = get_assigned_users(task)

	tier = RR.pre_deadline_reminder(days_left, settings.reminder_schedule, get_sent_tiers(task.name))
	if tier:
		send_email(task, CLIENT_TEMPLATE, [customer.email_id], tier)
		send_email(task, STAFF_TEMPLATE, staff, tier)
	elif RR.escalation_due(days_left, get_last_escalation(task.name), today_date, settings.overdue_repeat_days):
		tier = ESCALATION
		send_email(task, CLIENT_TEMPLATE, [customer.email_id], tier)
		send_email(task, STAFF_TEMPLATE, staff + get_users_with_role(MANAGER_ROLE), tier)

	critical = frappe.db.get_value("Item", task.custom_service, "custom_critical_deadline")
	if tier and settings.enable_sms and RR.sms_required(days_left, critical, settings.sms_threshold_days):
		send_sms(task, customer.mobile_no, tier)
	return tier


def get_sent_tiers(task_name):
	"""Reminder tiers already logged on this Task: the engine's 'sent_types' (no duplicates)."""
	return set(
		frappe.get_all(
			"Communication",
			filters={
				"reference_doctype": "Task",
				"reference_name": task_name,
				"custom_reminder_tier": ("is", "set"),
			},
			pluck="custom_reminder_tier",
		)
	)


def get_last_escalation(task_name):
	last = frappe.get_all(
		"Communication",
		filters={"reference_doctype": "Task", "reference_name": task_name, "custom_reminder_tier": ESCALATION},
		fields=["communication_date"],
		order_by="communication_date desc",
		limit=1,
	)
	return getdate(last[0].communication_date) if last else None


def get_assigned_users(task):
	"""Responsible staff = the users in the Task's standard Assign To."""
	return frappe.parse_json(task.get("_assign") or "[]")


def get_context(task, tier):
	"""Values for the Jinja placeholders in the Email Templates."""
	due = getdate(task.exp_end_date)
	days_left = S.days_to_due(due, getdate(today()))
	return {
		"customer_name": frappe.db.get_value("Customer", task.custom_customer, "customer_name"),
		"service": task.custom_service,
		"period": task.custom_period,
		"due_date": format_date(due),
		"days_left": days_left,
		# comparisons are done here, not in the template: Text Editor content escapes < and >
		"is_overdue": days_left < 0,
		"days_overdue": max(-days_left, 0),
    }

def send_email(task, template_name, recipients, tier):
	recipients = [r for r in recipients if r]
	if not recipients:
		return None
	template = frappe.get_cached_doc("Email Template", template_name)
	context = get_context(task, tier)
	comm = frappe.get_doc(
		{
			"doctype": "Communication",
			"communication_medium": "Email",
			"communication_type": "Automated Message",
			"sent_or_received": "Sent",
			"subject": frappe.render_template(template.subject, context),
			"content": frappe.render_template(template.response, context),
			"recipients": ", ".join(recipients),
			"reference_doctype": "Task",
			"reference_name": task.name,
			"custom_reminder_tier": tier,
		}
	).insert(ignore_permissions=True)
	if EmailAccount.find_outgoing():
		comm.send_email()  # queued in the standard Email Queue
	return comm.name


def send_sms(task, mobile_no, tier):
	if not mobile_no:
		return None
	context = get_context(task, tier)
	message = (
		f"{context['firm_name']}: {context['service']} {context['period']} is due on {context['due_date']}. "
		"Please send your documents."
	)
	has_gateway = bool(frappe.db.get_single_value("SMS Settings", "sms_gateway_url"))
	if has_gateway:
		from frappe.core.doctype.sms_settings.sms_settings import send_sms as send_via_sms_settings

		send_via_sms_settings([mobile_no], message, success_msg=False)  # also writes the standard SMS Log
	comm = frappe.get_doc(
		{
			"doctype": "Communication",
			"communication_medium": "SMS",
			"communication_type": "Automated Message",
			"sent_or_received": "Sent",
			"subject": f"SMS: {tier}",
			"content": message if has_gateway else f"[Not sent: no gateway in SMS Settings] {message}",
			"phone_no": mobile_no,
			"reference_doctype": "Task",
			"reference_name": task.name,
			"custom_reminder_tier": tier,
		}
	).insert(ignore_permissions=True)
	return comm.name
