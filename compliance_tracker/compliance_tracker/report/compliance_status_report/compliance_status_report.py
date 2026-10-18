import frappe
from frappe import _
from frappe.utils import flt, getdate, today

from compliance_tracker.engine import status as S

STATUS_ORDER = (S.ON_TRACK, S.AT_RISK, S.OVERDUE, S.COMPLETED_ON_TIME, S.COMPLETED_LATE)
STATUS_COLORS = ("#38a169", "#dd6b20", "#e53e3e", "#3182ce", "#d69e2e")

CHART_LABELS = ("On Track", "At Risk", "Overdue", "Filed On Time", "Filed Late")


def execute(filters=None):
	filters = frappe._dict(filters or {})
	data = get_data(filters)
	return get_columns(), data, None, get_chart(data), get_summary(data)


def get_columns():
	return [
		{"label": _("Task"), "fieldname": "task", "fieldtype": "Link", "options": "Task", "width": 140},
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 200},
		{"label": _("Service"), "fieldname": "service", "fieldtype": "Link", "options": "Item", "width": 130},
		{"label": _("Period"), "fieldname": "period", "fieldtype": "Data", "width": 130},
		{"label": _("Due Date"), "fieldname": "due_date", "fieldtype": "Date", "width": 100},
		{"label": _("Filed On"), "fieldname": "filed_on", "fieldtype": "Date", "width": 100},
		{"label": _("Days (+early / -late)"), "fieldname": "days", "fieldtype": "Int", "width": 90},
		{"label": _("Work Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
		{"label": _("Compliance Status"), "fieldname": "compliance_status", "fieldtype": "Data", "width": 150},
		{"label": _("Delay Responsibility"), "fieldname": "delay_responsibility", "fieldtype": "Data", "width": 130},
		{"label": _("Delay Reason"), "fieldname": "delay_reason", "fieldtype": "Data", "width": 200},
		{"label": _("Filing Reference"), "fieldname": "filing_reference", "fieldtype": "Data", "width": 140},
	]


def get_data(filters):
	conditions = {
		"custom_customer": ("is", "set"),
		"custom_service": ("is", "set"),
		"status": ("!=", "Cancelled"),
	}
	for filter_name, task_field in (
		("customer", "custom_customer"),
		("service", "custom_service"),
		("compliance_status", "custom_compliance_status"),
	):
		if filters.get(filter_name):
			conditions[task_field] = filters.get(filter_name)
	if filters.from_date and filters.to_date:
		conditions["exp_end_date"] = ("between", [filters.from_date, f"{filters.to_date} 23:59:59"])

	# get_list (not get_all): each user only sees the Tasks their standard ERPNext roles allow
	tasks = frappe.get_list(
		"Task",
		filters=conditions,
		fields=[
			"name",
			"custom_customer",
			"custom_service",
			"custom_period",
			"exp_end_date",
			"completed_on",
			"status",
			"custom_compliance_status",
			"custom_delay_responsibility",
			"custom_delay_reason",
			"custom_filing_reference",
		],
		order_by="exp_end_date asc",
		limit_page_length=0,
	)

	today_date = getdate(today())
	data = []
	for t in tasks:
		due = getdate(t.exp_end_date)
		filed = getdate(t.completed_on) if t.status == "Completed" and t.completed_on else None
		data.append(
			{
				"task": t.name,
				"customer": t.custom_customer,
				"service": t.custom_service,
				"period": t.custom_period,
				"due_date": due,
				"filed_on": filed,
				# open: days left (negative = overdue); filed: days early (negative = days late)
				"days": S.days_to_due(due, today_date, filed),
				"status": t.status,
				"compliance_status": t.custom_compliance_status,
				"delay_responsibility": t.custom_delay_responsibility,
				"delay_reason": t.custom_delay_reason,
				"filing_reference": t.custom_filing_reference,
			}
		)
	return data


def count(data, compliance_status):
	return len([d for d in data if d["compliance_status"] == compliance_status])


def get_chart(data):
	return {
		"data": {
			"labels": [_(label) for label in CHART_LABELS],
			"datasets": [{"name": _("Obligations"), "values": [count(data, s) for s in STATUS_ORDER]}],
		},
		"type": "donut",
		"colors": list(STATUS_COLORS),
	}



def get_summary(data):
	late = [d for d in data if d["compliance_status"] == S.COMPLETED_LATE]
	filed = count(data, S.COMPLETED_ON_TIME) + len(late)
	on_time_rate = flt(count(data, S.COMPLETED_ON_TIME) * 100 / filed, 1) if filed else 0

	def late_by(party):
		return len([d for d in late if d["delay_responsibility"] == party])

	return [
		{"label": _("Obligations"), "value": len(data), "datatype": "Int"},
		{
			"label": _("On-Time Filing Rate"),
			"value": on_time_rate,
			"datatype": "Percent",
			"indicator": "Green" if on_time_rate >= 90 else "Orange",
		},
		{"label": _("Overdue"), "value": count(data, S.OVERDUE), "datatype": "Int", "indicator": "Red"},
		{"label": _("At Risk"), "value": count(data, S.AT_RISK), "datatype": "Int", "indicator": "Orange"},
		{"label": _("Late - Client"), "value": late_by("Client"), "datatype": "Int"},
		{"label": _("Late - Firm"), "value": late_by("Firm"), "datatype": "Int", "indicator": "Red"},
		{"label": _("Late - Third Party"), "value": late_by("Third Party"), "datatype": "Int"},
	]
