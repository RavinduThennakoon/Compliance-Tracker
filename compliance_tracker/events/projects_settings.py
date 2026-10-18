import frappe
from frappe import _
from frappe.utils import cint

from compliance_tracker.engine.reminder_rules import parse_schedule
from compliance_tracker.settings import DEFAULTS


def validate(doc, method=None):
	"""Keep the compliance settings consistent when an admin saves Projects Settings."""
	schedule = parse_schedule(doc.custom_reminder_schedule, DEFAULTS["custom_reminder_schedule"])
	# store it cleaned: "3, 15,10,10" -> "15,10,3"
	doc.custom_reminder_schedule = ",".join(str(days) for days in schedule)

	if cint(doc.custom_generation_horizon_days) < schedule[0]:
		frappe.throw(
			_("Generation Horizon Days ({0}) must be at least the first reminder ({1} days).").format(
				doc.custom_generation_horizon_days, schedule[0]
			)
		)
