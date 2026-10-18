"""Compliance settings, stored as custom fields on the standard Projects Settings single."""

import frappe
from frappe.utils import cint

from compliance_tracker.engine.reminder_rules import parse_schedule

SETTINGS_DOCTYPE = "Projects Settings"

# Defaults: written on a new site by install.py, and used here if a value is missing
DEFAULTS = {
	"custom_reminder_schedule": "15,10,3",
	"custom_generation_horizon_days": 45,
	"custom_at_risk_days": 3,
	"custom_overdue_repeat_days": 7,
	"custom_enable_sms": 0,
	"custom_sms_threshold_days": 3,
}


def get_settings():
	"""All compliance settings as plain Python values, ready for the engine."""
	s = frappe.get_cached_doc(SETTINGS_DOCTYPE)

	def number(field):
		value = s.get(field)
		return DEFAULTS[field] if value in (None, "") else cint(value)

	return frappe._dict(
		reminder_schedule=parse_schedule(s.get("custom_reminder_schedule"), DEFAULTS["custom_reminder_schedule"]),
		generation_horizon_days=number("custom_generation_horizon_days"),
		at_risk_days=number("custom_at_risk_days"),
		overdue_repeat_days=number("custom_overdue_repeat_days"),
		enable_sms=number("custom_enable_sms"),
		sms_threshold_days=number("custom_sms_threshold_days"),
	)
