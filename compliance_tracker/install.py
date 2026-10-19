import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.modules.utils import sync_customizations
from frappe.utils.nestedset import get_root_of

from compliance_tracker.custom_fields import CUSTOM_FIELDS
from compliance_tracker.settings import DEFAULTS as SETTINGS_DEFAULTS, SETTINGS_DOCTYPE

ROLES = ["Compliance Manager", "Compliance Staff"]  # the portal uses ERPNext's standard "Customer" role

ITEM_GROUP = "Statutory Services"
TASK_TYPE = "Statutory Filing"
DAILY_JOB = "compliance_tracker.scheduler.run_daily"


CLIENT_TEMPLATE = "Compliance Reminder - Client"
STAFF_TEMPLATE = "Compliance Reminder - Staff"

# Default wording (Jinja). The firm can edit it later in Email Template; it is never overwritten.
EMAIL_TEMPLATES = {
	CLIENT_TEMPLATE: {
		"subject": "{{ reminder_tier }}: {{ service }} for {{ period }} is due on {{ due_date }}",
		"response": """<p>Dear {{ customer_name }},</p>
<p>This is a reminder that your <b>{{ service }}</b> filing for <b>{{ period }}</b> is due on
<b>{{ due_date }}</b>{% if is_overdue %} and is now <b>{{ days_overdue }} day(s) overdue</b>{% else %}
({{ days_left }} day(s) from today){% endif %}.</p>
<p>Please send us any outstanding documents so that we can file on time.</p>
{% if penalty_advisory %}<p><i>{{ penalty_advisory }}</i></p>{% endif %}
<p>Thank you,<br>{{ firm_name }}</p>""",
	},
	STAFF_TEMPLATE: {
		"subject": "[{{ compliance_status }}] {{ service }} - {{ period }} - {{ customer_name }} (due {{ due_date }})",
		"response": """<p>{{ reminder_tier }} for <b>{{ customer_name }}</b>:</p>
<ul>
<li>Service: {{ service }} ({{ period }})</li>
<li>Due date: {{ due_date }}</li>
<li>Compliance status: <b>{{ compliance_status }}</b></li>
<li>Task: <a href="{{ task_url }}">{{ task }}</a></li>
</ul>
<p>{{ firm_name }} - Compliance Tracker</p>""",
	},
}

# Default Sri Lankan statutory services. Due days / offsets are configurable
# defaults and should be confirmed against the latest IRD / ROC notices.
SERVICES = [
	# item name, statutory body, frequency, due_day, months_after_period_end, critical, penalty advisory
	("VAT", "Inland Revenue Department (IRD)", "Monthly", 20, 1, 1,
	 "Late VAT filing/payment may attract penalties (e.g. LKR 50,000 + 5% of unpaid tax) and interest of about 1.5% per month."),
	("APIT", "Inland Revenue Department (IRD)", "Monthly", 15, 1, 1,
	 "Unremitted APIT attracts penalties and interest; employees may become jointly liable."),
	("SSCL", "Inland Revenue Department (IRD)", "Quarterly", 20, 1, 1,
	 "Late SSCL payment may attract penalties and interest."),
	("EPF", "EPF / ETF Authorities", "Monthly", 31, 1, 1,
	 "Late EPF contributions attract surcharges."),
	("ETF", "EPF / ETF Authorities", "Monthly", 31, 1, 0,
	 "Late ETF contributions attract surcharges."),
	("Income Tax Return", "Inland Revenue Department (IRD)", "Annual", 30, 8, 1,
	 "Late income tax returns may attract penalties and interest."),
	("Annual Audit", "Internal (Firm)", "Annual", 30, 6, 0, None),
	("ROC Annual Return", "Registrar of Companies (ROC)", "Annual", 31, 7, 1,
	 "Late filing with the Registrar of Companies may attract late fees."),
	("Bookkeeping", "Internal (Firm)", "Monthly", 10, 1, 0, None),
]


def after_install():
	# Frappe runs after_install BEFORE it syncs this app's custom fields,
	# so sync them first: the service Items below use those fields.
	sync_customizations("compliance_tracker")
	setup()


def after_migrate():
	setup()


def setup():
	"""Idempotent: safe to run on every install and migrate."""
	create_roles()
	harden_portal()
	create_item_group()
	create_service_items()
	create_task_type()
	create_email_templates()
	create_custom_fields(CUSTOM_FIELDS)  # fields that cannot be made in Customize Form (Single DocTypes)
	init_settings()
	frappe.db.commit()


def create_roles():
	for role in ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)
	# The client portal relies on ERPNext's "Customer" role being website-only (ERPNext's own
	# installer intends desk_access = 0, but it is not always applied), so enforce it here.
	if frappe.db.exists("Role", "Customer"):
		frappe.db.set_value("Role", "Customer", "desk_access", 0)

def harden_portal():
	"""Clients (ERPNext "Customer" role) must reach only the read-only /my-compliance page."""
	# ERPNext intends the Customer role to be website-only (desk_access = 0), but it is not always applied
	if frappe.db.exists("Role", "Customer"):
		frappe.db.set_value("Role", "Customer", "desk_access", 0)
	# ERPNext's standard "tasks" web form lets any logged-in website user create Tasks
	if frappe.db.exists("Web Form", "tasks"):
		frappe.db.set_value("Web Form", "tasks", "published", 0)


def enable_job_log():
	"""Keep a Scheduled Job Log entry for every run of the daily job, as evidence that it runs by itself."""
	frappe.db.set_value("Scheduled Job Type", {"method": DAILY_JOB}, "create_log", 1)


def create_item_group():
	if not frappe.db.exists("Item Group", ITEM_GROUP):
		frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": ITEM_GROUP,
				"parent_item_group": get_root_of("Item Group"),
				"is_group": 0,
			}
		).insert(ignore_permissions=True)


def create_service_items():
	for name, body, freq, day, offset, critical, advisory in SERVICES:
		if frappe.db.exists("Item", name):
			continue  # never overwrite a rule the firm has changed
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": name,
				"item_name": name,
				"item_group": ITEM_GROUP,
				"stock_uom": "Nos",
				"is_stock_item": 0,
				"include_item_in_manufacturing": 0,
				"description": f"{name} compliance service",
				"custom_statutory_body": body,
				"custom_filing_frequency": freq,
				"custom_due_day": day,
				"custom_months_after_period_end": offset,
				"custom_critical_deadline": critical,
				"custom_penalty_advisory": advisory,
			}
		).insert(ignore_permissions=True)
def create_task_type():
	if not frappe.db.exists("Task Type", TASK_TYPE):
		frappe.get_doc(
			{
				"doctype": "Task Type",
				"name": TASK_TYPE,  # Task Type is named by the user ("Prompt"), so the name is set directly
				"description": "Statutory compliance obligation generated by Compliance Tracker",
			}
		).insert(ignore_permissions=True)

def init_settings():
	"""Write a default only for settings that were never saved, so an admin's value is never overwritten."""
	for field, value in SETTINGS_DEFAULTS.items():
		saved = frappe.db.sql(
			"select 1 from `tabSingles` where doctype=%s and field=%s", (SETTINGS_DOCTYPE, field)
		)
		if not saved:
			frappe.db.set_single_value(SETTINGS_DOCTYPE, field, value)
def create_email_templates():
	for name, template in EMAIL_TEMPLATES.items():
		if not frappe.db.exists("Email Template", name):
			frappe.get_doc(
				{
					"doctype": "Email Template",
					"name": name,  # Email Template is named by the user ("Prompt")
					"subject": template["subject"],
					"response": template["response"],
				}
			).insert(ignore_permissions=True)


