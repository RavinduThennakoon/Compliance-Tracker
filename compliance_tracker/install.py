import frappe
from frappe.modules.utils import sync_customizations
from frappe.utils.nestedset import get_root_of

ROLES = ["Compliance Manager", "Compliance Staff"]  # the portal uses ERPNext's standard "Customer" role

ITEM_GROUP = "Statutory Services"

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
	create_item_group()
	create_service_items()
	frappe.db.commit()


def create_roles():
	for role in ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)


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
