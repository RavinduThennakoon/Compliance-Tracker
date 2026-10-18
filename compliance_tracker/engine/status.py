"""
Compliance Status Classifier
============================

Pure function that assigns the traffic-light compliance status of an
obligation:

    On Track          (green)  - more than ``at_risk_days`` left
    At Risk           (amber)  - due within ``at_risk_days`` days (incl. today)
    Overdue           (red)    - due date has passed and not filed
    Completed On Time          - filed on/before the due date
    Completed Late             - filed after the due date
"""

from __future__ import annotations

from datetime import date

ON_TRACK = "On Track"
AT_RISK = "At Risk"
OVERDUE = "Overdue"
COMPLETED_ON_TIME = "Completed On Time"
COMPLETED_LATE = "Completed Late"

OPEN_STATUSES = (ON_TRACK, AT_RISK, OVERDUE)


def days_to_due(due_date: date, today: date, filed_on: date | None = None) -> int:
	"""Open: days left (negative = days overdue). Filed: days filed before due (negative = days late)."""
	return (due_date - (filed_on or today)).days


def classify(due_date: date, today: date, filed_on: date | None = None, at_risk_days: int = 3) -> str:
	if filed_on:
		return COMPLETED_ON_TIME if filed_on <= due_date else COMPLETED_LATE
	left = days_to_due(due_date, today)
	if left < 0:
		return OVERDUE
	if left <= at_risk_days:
		return AT_RISK
	return ON_TRACK
