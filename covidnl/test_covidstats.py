from unittest import TestCase

from covidnl.model import CaseFilter, CovidCase


class TestCaseFilter(TestCase):
	
	def test_process_age_filter(self):
		single_range_exact = CaseFilter.process_age_filter("20-29")
		single_range_inexact = CaseFilter.process_age_filter("22-28")
		single_range_no_end = CaseFilter.process_age_filter("22")
		
		multiple_ranges_exact = CaseFilter.process_age_filter("20-49")
		multiple_ranges_inexact = CaseFilter.process_age_filter("24-45")
		
		self.assertEqual(single_range_exact, ("20-29",), "Single exact range failed")
		self.assertEqual(single_range_inexact, ("20-29",), "Single inexact range failed")
		self.assertEqual(single_range_no_end, ("20-29",), "Single endless range failed")
		
		self.assertEqual(multiple_ranges_exact, ("20-29", "30-39", "40-49"), "Multiple exact ranges failed")
		self.assertEqual(multiple_ranges_inexact, ("20-29", "30-39", "40-49"), "Multiple inexact ranges failed")
	
	def test_filter(self):
		matching_both_case = CovidCase("2020-10-04", "30-39", "Male", "Zuid-Holland", "No", "No")
		matching_age_case = CovidCase("2020-10-04", "30-39", "Male", "Noord-Holland", "No", "No")
		matching_province_case = CovidCase("2020-10-04", "50-59", "Male", "Zuid-Holland", "No", "No")
		matching_none_case = CovidCase("2020-10-04", "50-59", "Male", "Noord-Holland", "No", "No")
		
		blank_filter = CaseFilter()
		province_filter = CaseFilter("Zuid-Holland")
		age_filter = CaseFilter(age_filter="20-39")
		dual_filter = CaseFilter("Zuid-Holland", "20-39")
		
		for c_case in (matching_age_case, matching_both_case, matching_province_case, matching_none_case):
			self.assertTrue(blank_filter.filter(c_case))
		
		for c_case in (matching_age_case, matching_both_case):
			self.assertTrue(age_filter.filter(c_case))
		for c_case in (matching_province_case, matching_none_case):
			self.assertFalse(age_filter.filter(c_case))
		
		for c_case in (matching_province_case, matching_both_case):
			self.assertTrue(province_filter.filter(c_case))
		for c_case in (matching_age_case, matching_none_case):
			self.assertFalse(province_filter.filter(c_case))
		
		self.assertTrue(dual_filter.filter(matching_both_case))
		for c_case in (matching_age_case, matching_province_case, matching_none_case):
			self.assertFalse(dual_filter.filter(c_case))
