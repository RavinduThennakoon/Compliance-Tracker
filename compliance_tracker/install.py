import frappe

ROLES = [
	("Compliance Manager", 1),
	("Compliance Staff", 1),
	("Compliance Client", 0),  # portal only - no Desk access
]

# Default Sri Lankan statutory services. Due days / offsets are configurable
# defaults and should be confirmed against the latest IRD / ROC notices.
SERVICE_TYPES = [
	# name, body, frequency, due_day, offset_months, critical, advisory
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
	create_roles()
	create_service_types()
	init_settings()
	frappe.db.commit()


def after_migrate():
	create_roles()
	init_settings()


def create_roles():
	for role, desk in ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": desk}).insert(ignore_permissions=True)
		else:
			frappe.db.set_value("Role", role, "desk_access", desk)


def create_service_types():
	for name, body, freq, day, offset, critical, advisory in SERVICE_TYPES:
		if frappe.db.exists("Statutory Service", name):
			continue
		frappe.get_doc(
			{
				"doctype": "Statutory Service",
				"service_name": name,
				"statutory_body": body,
				"default_frequency": freq,
				"default_due_day": day,
				"default_due_offset_months": offset,
				"is_critical": critical,
				"advisory_note": advisory,
			}
		).insert(ignore_permissions=True)


def init_settings():
	"""Fill default settings once (only if the settings DocType exists and was never configured)."""
	if not frappe.db.exists("DocType", "Compliance Settings"):
		return
	# get_single() returns form defaults even before the first save, so check the database itself
	if frappe.db.sql("select value from `tabSingles` where doctype='Compliance Settings' and field='firm_name' and value!=''"):
		return  # already configured by an administrator - never overwrite
	s = frappe.get_single("Compliance Settings")
	defaults = {
		"firm_name": "SmartAudit & Co.",
		"generation_horizon_days": 45,
		"fy_start_month": 4,
		"enable_email_reminders": 1,
		"reminder_schedule": "15,10,3",
		"at_risk_days": 3,
		"notify_staff": 1,
		"overdue_repeat_days": 7,
		"enable_sms": 1,
		"sms_mode": "Mock (log only)",
		"sms_threshold_days": 3,
	}
	for k, v in defaults.items():
		if not s.get(k):
			s.set(k, v)
	s.flags.ignore_permissions = True
	s.save()
