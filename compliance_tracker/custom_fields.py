"""Custom fields created from code.

Frappe does not allow Single DocTypes (such as Projects Settings) to be customized
from Customize Form, so their fields are defined here and created by install.py.
"""

MODULE = "Compliance Tracker"

CUSTOM_FIELDS = {
	"Projects Settings": [
		{
			"fieldname": "custom_compliance_reminders",
			"label": "Compliance Reminders",
			"fieldtype": "Section Break",
			"insert_after": "fetch_timesheet_in_sales_invoice",
			"module": MODULE,
		},
		{
			"fieldname": "custom_reminder_schedule",
			"label": "Reminder Schedule",
			"fieldtype": "Data",
			"default": "15,10,3",
			"description": "Days before the due date, comma separated",
			"insert_after": "custom_compliance_reminders",
			"module": MODULE,
		},
		{
			"fieldname": "custom_generation_horizon_days",
			"label": "Generation Horizon Days",
			"fieldtype": "Int",
			"default": "45",
			"description": "Create obligations this many days before they are due",
			"insert_after": "custom_reminder_schedule",
			"module": MODULE,
		},
		{
			"fieldname": "custom_at_risk_days",
			"label": "At Risk Days",
			"fieldtype": "Int",
			"default": "3",
			"description": "Days before due when an obligation turns At Risk",
			"insert_after": "custom_generation_horizon_days",
			"module": MODULE,
		},
		{
			"fieldname": "custom_overdue_repeat_days",
			"label": "Overdue Repeat Days",
			"fieldtype": "Int",
			"default": "7",
			"description": "Repeat the overdue escalation every N days",
			"insert_after": "custom_at_risk_days",
			"module": MODULE,
		},
		{
			"fieldname": "custom_compliance_column",
			"fieldtype": "Column Break",
			"insert_after": "custom_overdue_repeat_days",
			"module": MODULE,
		},
		{
			"fieldname": "custom_enable_sms",
			"label": "Enable SMS",
			"fieldtype": "Check",
			"default": "0",
			"description": "SMS for critical services, via the standard SMS Settings",
			"insert_after": "custom_compliance_column",
			"module": MODULE,
		},
		{
			"fieldname": "custom_sms_threshold_days",
			"label": "SMS Threshold Days",
			"fieldtype": "Int",
			"default": "3",
			"depends_on": "eval:doc.custom_enable_sms",
			"insert_after": "custom_enable_sms",
			"module": MODULE,
		},
		{
			"fieldname": "custom_last_run_summary",
			"label": "Last Run Summary",
			"fieldtype": "Small Text",
			"read_only": 1,
			"insert_after": "custom_sms_threshold_days",
			"module": MODULE,
		},
	],
}
