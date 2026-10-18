"""
Multi-Tier Reminder Rules
=========================

Pure decision logic used by the daily reminder job.

1. Pre-deadline reminders (default tiers 15, 10 and 3 days before due):
   the job sends the *closest tier already reached* that has not yet been
   sent. This makes the engine self-healing: if the server was down on the
   day the 10-day reminder should have gone out, it is sent on the next run
   instead of being silently skipped, and stale tiers are never sent twice.

2. SMS: for services flagged as *critical*, an SMS is sent in addition to
   e-mail once the deadline is within ``sms_threshold_days`` days or overdue.

3. Overdue escalation: once an obligation is overdue the responsible staff
   member and the manager are alerted, repeated every
   ``overdue_repeat_days`` days until the obligation is filed.
"""

from __future__ import annotations

from datetime import date


def parse_schedule(value: str | None, default: str = "15,10,3") -> list[int]:
	"""'15, 10,3' -> [15, 10, 3] (unique, positive, descending)."""
	raw = (value or default).replace(";", ",")
	tiers = set()
	for part in raw.split(","):
		part = part.strip()
		if part.isdigit() and int(part) > 0:
			tiers.add(int(part))
	if not tiers:
		return parse_schedule(default)
	return sorted(tiers, reverse=True)


def tier_label(days: int) -> str:
	return f"{days}-Day Reminder"


def pre_deadline_reminder(days_left: int, schedule: list[int], sent_types: set[str]) -> str | None:
	"""Return the reminder type to send today, or None."""
	if days_left < 0:
		return None
	reached = [t for t in schedule if days_left <= t]
	if not reached:
		return None
	target = tier_label(min(reached))
	return None if target in sent_types else target


def escalation_due(days_left: int, last_escalation: date | None, today: date, repeat_days: int = 7) -> bool:
	"""Overdue escalation: first day overdue, then every ``repeat_days`` days."""
	if days_left >= 0:
		return False
	if last_escalation is None:
		return True
	return (today - last_escalation).days >= max(1, int(repeat_days or 7))


def sms_required(days_left: int, is_critical: bool, sms_threshold_days: int = 3) -> bool:
	return bool(is_critical) and days_left <= int(sms_threshold_days)
