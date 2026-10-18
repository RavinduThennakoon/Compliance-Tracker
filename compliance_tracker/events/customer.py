import frappe
from frappe import _

from compliance_tracker.install import ITEM_GROUP


def validate(doc, method=None):
	validate_compliance_services(doc)


def validate_compliance_services(doc):
	"""One active row per service, only statutory service Items, and a complete due-date rule."""
	seen = set()
	for row in doc.get("custom_compliance_services") or []:
		if frappe.db.get_value("Item", row.service, "item_group") != ITEM_GROUP:
			frappe.throw(_("Row {0}: {1} is not a statutory service.").format(row.idx, frappe.bold(row.service)))

		if row.active:
			if row.service in seen:
				frappe.throw(
					_("Row {0}: {1} is already an active service for this customer.").format(
						row.idx, frappe.bold(row.service)
					)
				)
			seen.add(row.service)

		if row.frequency == "One-off":
			if not row.one_off_due_date:
				frappe.throw(_("Row {0}: please set the One-off Due Date for {1}.").format(row.idx, row.service))
		elif not row.due_day or not 1 <= row.due_day <= 31:
			frappe.throw(_("Row {0}: Due Day for {1} must be between 1 and 31.").format(row.idx, row.service))
