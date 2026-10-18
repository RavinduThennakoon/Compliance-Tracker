"""
Due-Date Engine (recurrence rules)
==================================

Pure-Python logic (no Frappe dependency) that turns a recurring statutory
service (e.g. VAT - monthly, SSCL - quarterly, Income Tax - annual) into a
concrete list of compliance periods and their statutory due dates.

Rule used for every frequency:

    due date = day ``due_day`` of the month that is ``due_offset_months``
               months after the month in which the period ends.

Examples (Sri Lankan context, defaults shipped with the app):

    VAT  (Monthly,   offset 1, day 20) -> Oct 2026 period is due 20 Nov 2026
    SSCL (Quarterly, offset 1, day 20) -> Jul-Sep 2026 is due 20 Oct 2026
    Income Tax (Annual Y/A Apr-Mar, offset 8, day 30)
                                       -> Y/A 2025/2026 is due 30 Nov 2026

If ``due_day`` is larger than the number of days in the target month the
last day of that month is used (e.g. day 31 in November -> 30 November).
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date

MONTHLY = "Monthly"
QUARTERLY = "Quarterly"
ANNUAL = "Annual"
ONE_OFF = "One-off"

FREQUENCIES = (MONTHLY, QUARTERLY, ANNUAL, ONE_OFF)

# Sri Lankan year of assessment runs 1 April - 31 March.
DEFAULT_FY_START_MONTH = 4

MONTH_ABBR = calendar.month_abbr


@dataclass(frozen=True)
class Period:
	start: date
	end: date
	label: str
	due_date: date


def add_months(year: int, month: int, n: int) -> tuple[int, int]:
	"""Return (year, month) shifted by ``n`` months."""
	index = year * 12 + (month - 1) + n
	return index // 12, index % 12 + 1


def safe_date(year: int, month: int, day: int) -> date:
	"""Build a date, clamping ``day`` to the last valid day of the month."""
	last = calendar.monthrange(year, month)[1]
	day = max(1, min(int(day or last), last))
	return date(year, month, day)


def month_end(year: int, month: int) -> date:
	return date(year, month, calendar.monthrange(year, month)[1])


def period_containing(frequency: str, ref: date, fy_start_month: int = DEFAULT_FY_START_MONTH) -> tuple[date, date, str]:
	"""Return (start, end, label) of the period of ``frequency`` that contains ``ref``."""
	if frequency == MONTHLY:
		start = date(ref.year, ref.month, 1)
		end = month_end(ref.year, ref.month)
		label = f"{MONTH_ABBR[ref.month]} {ref.year}"
	elif frequency == QUARTERLY:
		q = (ref.month - 1) // 3  # calendar quarters Jan-Mar, Apr-Jun, Jul-Sep, Oct-Dec
		sm = q * 3 + 1
		start = date(ref.year, sm, 1)
		end = month_end(ref.year, sm + 2)
		label = f"Q{q + 1} {ref.year} ({MONTH_ABBR[sm]}-{MONTH_ABBR[sm + 2]})"
	elif frequency == ANNUAL:
		sy = ref.year if ref.month >= fy_start_month else ref.year - 1
		start = date(sy, fy_start_month, 1)
		ey, em = add_months(sy, fy_start_month, 11)
		end = month_end(ey, em)
		label = f"Y/A {sy}/{sy + 1}" if fy_start_month != 1 else f"Year {sy}"
	else:
		raise ValueError(f"Unsupported recurring frequency: {frequency!r}")
	return start, end, label


def due_date_for(period_end: date, due_day: int, due_offset_months: int) -> date:
	"""Statutory due date for a period that ends on ``period_end``."""
	y, m = add_months(period_end.year, period_end.month, int(due_offset_months or 0))
	return safe_date(y, m, due_day)


def next_period_start(frequency: str, period_end: date) -> date:
	y, m = add_months(period_end.year, period_end.month, 1)
	return date(y, m, 1)


def generate_periods(
	frequency: str,
	service_start: date,
	up_to_due_date: date,
	due_day: int,
	due_offset_months: int,
	fy_start_month: int = DEFAULT_FY_START_MONTH,
	one_off_due_date: date | None = None,
	max_periods: int = 500,
) -> list[Period]:
	"""
	All periods of a service, starting with the period that contains
	``service_start``, whose due date falls on or before ``up_to_due_date``.

	This is what the scheduler calls daily with
	``up_to_due_date = today + generation horizon`` so that every obligation
	exists in the system early enough for the first (e.g. 15-day) reminder.
	"""
	if frequency == ONE_OFF:
		if not one_off_due_date:
			return []
		if one_off_due_date > up_to_due_date:
			return []
		return [Period(service_start, one_off_due_date, f"One-off ({one_off_due_date.isoformat()})", one_off_due_date)]

	periods: list[Period] = []
	start, end, label = period_containing(frequency, service_start, fy_start_month)
	while len(periods) < max_periods:
		due = due_date_for(end, due_day, due_offset_months)
		if due > up_to_due_date:
			break
		periods.append(Period(start, end, label, due))
		start, end, label = period_containing(frequency, next_period_start(frequency, end), fy_start_month)
	return periods
