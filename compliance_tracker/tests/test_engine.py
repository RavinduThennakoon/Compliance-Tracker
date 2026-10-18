"""
Unit tests for the pure computational engine (no database needed).

Run inside the bench:   bench --site <site> run-tests --module compliance_tracker.tests.test_engine
Run standalone:         python -m unittest compliance_tracker.tests.test_engine   (from the app folder)
"""

import unittest
from datetime import date

from compliance_tracker.engine import recurrence as R
from compliance_tracker.engine import reminder_rules as RR
from compliance_tracker.engine import status as S


class TestDueDateEngine(unittest.TestCase):
	# --- due date rule ------------------------------------------------------
	def test_vat_monthly_due_20th_next_month(self):
		start, end, label = R.period_containing(R.MONTHLY, date(2026, 10, 7))
		self.assertEqual((start, end, label), (date(2026, 10, 1), date(2026, 10, 31), "Oct 2026"))
		self.assertEqual(R.due_date_for(end, 20, 1), date(2026, 11, 20))

	def test_december_rolls_into_next_year(self):
		_, end, _ = R.period_containing(R.MONTHLY, date(2026, 12, 15))
		self.assertEqual(R.due_date_for(end, 20, 1), date(2027, 1, 20))

	def test_last_day_clamping_epf(self):
		# EPF due "last day of following month": day 31 in a 30-day / 28-day month
		self.assertEqual(R.due_date_for(date(2026, 10, 31), 31, 1), date(2026, 11, 30))
		self.assertEqual(R.due_date_for(date(2027, 1, 31), 31, 1), date(2027, 2, 28))
		self.assertEqual(R.due_date_for(date(2028, 1, 31), 31, 1), date(2028, 2, 29))  # leap year

	def test_quarterly_sscl(self):
		start, end, label = R.period_containing(R.QUARTERLY, date(2026, 8, 14))
		self.assertEqual((start, end), (date(2026, 7, 1), date(2026, 9, 30)))
		self.assertEqual(label, "Q3 2026 (Jul-Sep)")
		self.assertEqual(R.due_date_for(end, 20, 1), date(2026, 10, 20))

	def test_annual_year_of_assessment_april_march(self):
		start, end, label = R.period_containing(R.ANNUAL, date(2026, 2, 1))
		self.assertEqual((start, end, label), (date(2025, 4, 1), date(2026, 3, 31), "Y/A 2025/2026"))
		self.assertEqual(R.due_date_for(end, 30, 8), date(2026, 11, 30))  # income tax return

	def test_annual_after_april(self):
		start, end, label = R.period_containing(R.ANNUAL, date(2026, 4, 1))
		self.assertEqual(label, "Y/A 2026/2027")
		self.assertEqual(end, date(2027, 3, 31))

	def test_calendar_year_option(self):
		_, end, label = R.period_containing(R.ANNUAL, date(2026, 6, 1), fy_start_month=1)
		self.assertEqual((end, label), (date(2026, 12, 31), "Year 2026"))

	# --- period generation ---------------------------------------------------
	def test_generate_monthly_periods_up_to_horizon(self):
		periods = R.generate_periods(R.MONTHLY, date(2026, 7, 10), date(2026, 11, 30), 20, 1)
		self.assertEqual([p.label for p in periods], ["Jul 2026", "Aug 2026", "Sep 2026", "Oct 2026"])
		self.assertEqual([p.due_date for p in periods][-1], date(2026, 11, 20))

	def test_generate_respects_service_start(self):
		periods = R.generate_periods(R.MONTHLY, date(2026, 10, 1), date(2026, 12, 31), 15, 1)
		self.assertEqual(periods[0].label, "Oct 2026")

	def test_generate_quarterly(self):
		periods = R.generate_periods(R.QUARTERLY, date(2026, 1, 1), date(2026, 12, 31), 20, 1)
		self.assertEqual(len(periods), 3)  # Q1, Q2, Q3 (Q4 is due Jan 2027)
		self.assertEqual(periods[-1].due_date, date(2026, 10, 20))

	def test_generate_one_off(self):
		p = R.generate_periods(R.ONE_OFF, date(2026, 9, 1), date(2026, 12, 31), 0, 0, one_off_due_date=date(2026, 11, 5))
		self.assertEqual(len(p), 1)
		self.assertEqual(p[0].due_date, date(2026, 11, 5))
		self.assertEqual(
			R.generate_periods(R.ONE_OFF, date(2026, 9, 1), date(2026, 10, 31), 0, 0, one_off_due_date=date(2026, 11, 5)),
			[],
		)

	def test_no_duplicate_labels_over_long_range(self):
		periods = R.generate_periods(R.MONTHLY, date(2020, 1, 1), date(2030, 12, 31), 20, 1)
		labels = [p.label for p in periods]
		self.assertEqual(len(labels), len(set(labels)))
		self.assertEqual(len(labels), 131)  # Jan 2020 .. Nov 2030 (Dec 2030 due Jan 2031)

	def test_invalid_frequency(self):
		with self.assertRaises(ValueError):
			R.period_containing("Weekly", date(2026, 1, 1))


class TestStatusClassifier(unittest.TestCase):
	due = date(2026, 11, 20)

	def test_on_track(self):
		self.assertEqual(S.classify(self.due, date(2026, 11, 10)), S.ON_TRACK)

	def test_at_risk_boundary(self):
		self.assertEqual(S.classify(self.due, date(2026, 11, 17)), S.AT_RISK)  # 3 days
		self.assertEqual(S.classify(self.due, date(2026, 11, 16)), S.ON_TRACK)  # 4 days
		self.assertEqual(S.classify(self.due, date(2026, 11, 20)), S.AT_RISK)  # due today

	def test_overdue(self):
		self.assertEqual(S.classify(self.due, date(2026, 11, 21)), S.OVERDUE)

	def test_days_to_due_open_and_filed(self):
		self.assertEqual(S.days_to_due(self.due, date(2026, 11, 10)), 10)
		self.assertEqual(S.days_to_due(self.due, date(2026, 11, 25)), -5)
		self.assertEqual(S.days_to_due(self.due, date(2027, 1, 1), filed_on=date(2026, 11, 18)), 2)
		self.assertEqual(S.days_to_due(self.due, date(2027, 1, 1), filed_on=date(2026, 11, 23)), -3)

	def test_completed(self):
		self.assertEqual(S.classify(self.due, date(2026, 12, 1), filed_on=date(2026, 11, 20)), S.COMPLETED_ON_TIME)
		self.assertEqual(S.classify(self.due, date(2026, 12, 1), filed_on=date(2026, 11, 22)), S.COMPLETED_LATE)


class TestReminderRules(unittest.TestCase):
	schedule = [15, 10, 3]

	def test_parse_schedule(self):
		self.assertEqual(RR.parse_schedule("3, 15,10,10"), [15, 10, 3])
		self.assertEqual(RR.parse_schedule("abc"), [15, 10, 3])
		self.assertEqual(RR.parse_schedule(None), [15, 10, 3])

	def test_exact_tiers(self):
		self.assertEqual(RR.pre_deadline_reminder(15, self.schedule, set()), "15-Day Reminder")
		self.assertEqual(RR.pre_deadline_reminder(10, self.schedule, {"15-Day Reminder"}), "10-Day Reminder")
		self.assertEqual(RR.pre_deadline_reminder(3, self.schedule, {"15-Day Reminder", "10-Day Reminder"}), "3-Day Reminder")

	def test_no_reminder_outside_tiers(self):
		self.assertIsNone(RR.pre_deadline_reminder(20, self.schedule, set()))

	def test_no_duplicate(self):
		self.assertIsNone(RR.pre_deadline_reminder(14, self.schedule, {"15-Day Reminder"}))

	def test_catch_up_after_missed_run(self):
		# server down on day 10 -> on day 8 the 10-day reminder is sent (not the stale 15-day one)
		self.assertEqual(RR.pre_deadline_reminder(8, self.schedule, set()), "10-Day Reminder")

	def test_no_pre_deadline_when_overdue(self):
		self.assertIsNone(RR.pre_deadline_reminder(-1, self.schedule, set()))

	def test_escalation(self):
		today = date(2026, 11, 25)
		self.assertFalse(RR.escalation_due(0, None, today))
		self.assertTrue(RR.escalation_due(-1, None, today))
		self.assertFalse(RR.escalation_due(-3, date(2026, 11, 23), today, 7))
		self.assertTrue(RR.escalation_due(-8, date(2026, 11, 18), today, 7))

	def test_sms_only_for_critical_near_deadline(self):
		self.assertTrue(RR.sms_required(3, True))
		self.assertTrue(RR.sms_required(-2, True))
		self.assertFalse(RR.sms_required(10, True))
		self.assertFalse(RR.sms_required(1, False))


if __name__ == "__main__":
	unittest.main()
