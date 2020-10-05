import datetime
from typing import List, Tuple, Dict

import numpy as np

from covidnl.model import CovidCase, CaseFilter


def calculate_smoothed_trends(case_counts: np.ndarray, death_counts: np.ndarray, smoothing_window: int) -> Tuple[np.ndarray, np.ndarray]:
	"""
	Calculates the smoothed trends with the given smoothing window
	:param case_counts: Cases per day
	:param death_counts: Deaths per day
	:param smoothing_window: How many days should the smoothing look behind
	:return: A tuple of NumPy arrays: (smoothed_cases, smoothed_deaths)
	"""
	smoothed_cases: np.ndarray = np.zeros(len(case_counts))
	smoothed_deaths: np.ndarray = np.zeros(len(case_counts))
	for day_idx in range(smoothing_window, len(case_counts) + 1):
		case_sum = sum(case_counts[day_idx - smoothing_window:day_idx:])
		death_sum = sum(death_counts[day_idx - smoothing_window:day_idx:])
		
		smoothed_cases[day_idx - 1] = case_sum / smoothing_window
		smoothed_deaths[day_idx - 1] = death_sum / smoothing_window
	return smoothed_cases, smoothed_deaths


def count_cumulative_cases(
		days: List[datetime.date],
		cases_per_day: Dict[datetime.date, int],
		deaths_per_day: Dict[datetime.date, int]) -> Tuple[List[int], List[int]]:
	"""
	Calculates the cumulative cases and deaths
	:param days: The list of days with at least one case or death
	:param cases_per_day: A dictionary of case counts indexed by days
	:param deaths_per_day: A dictionary of death counts indexed by days
	:return: A tuple of lists containing the cumulative cases and cumulative deaths: (cumulative_cases, cumulative_deaths)
	"""
	cumulative_cases: List[int] = list()
	cumulative_deaths: List[int] = list()
	cumulative_cases.append(cases_per_day[days[0]])
	cumulative_deaths.append(0)
	for day in days[1::]:
		cumulative_cases.append(cumulative_cases[-1] + cases_per_day.get(day, 0))  # Again, my world-famous optimism.
		cumulative_deaths.append(cumulative_deaths[-1] + deaths_per_day.get(day, 0))
	return cumulative_cases, cumulative_deaths


def separate_stacks(
		cases: List[CovidCase],
		days: List[datetime.date],
		cutoff_day: datetime.date,
		stack: str,
		case_filter: CaseFilter) -> Tuple[Tuple[str, ...], np.ndarray]:
	"""
	Returns the data represented as separate data lines by the stacking category
	:param cases: A list of all CovidCase cases
	:param days: A list of days (datetime.date)
	:param cutoff_day: A cutoff date (datetime.date)
	:param stack: The stacking parameter. String, one of "province", "sex", or "age".
	:param case_filter: A CaseFilter object
	:return: A tuple consisting of a list of stack labels (strings) and a 2D NumPy array, first dimension: stack, second dimension: day.
	"""
	if stack == "province":
		stack_labels: Tuple[str, ...] = provinces
	elif stack == "sex":
		stack_labels = ("Male", "Female")
	else:
		stack_labels = case_filter.age_filter if case_filter.age_filter is not None else (
			"Unknown",
			"0-9",
			"10-19",
			"20-29",
			"30-39",
			"40-49",
			"50-59",
			"60-69",
			"70-79",
			"80-89",
			"90+"
		)
	stacked_cases_per_day: np.ndarray = np.zeros((len(stack_labels), len(days)), dtype=int)
	for c_case in cases:
		if c_case.day > cutoff_day:
			# Skip recent values, those days are most likely incomplete.
			continue
		if not case_filter.filter(c_case):
			continue
		stack_key = c_case.province if stack == "province" else (c_case.sex if stack == "sex" else c_case.age)
		if stack_key in stack_labels:
			stack_idx = stack_labels.index(stack_key)
			day_idx = days.index(c_case.day)
			stacked_cases_per_day[stack_idx][day_idx] += 1
	return stack_labels, stacked_cases_per_day


def calculate_r_rate_data(case_counts: np.ndarray, cumulative_cases: List[int]) -> Tuple[List[int], np.ndarray, List[float], List[int], List[float]]:
	"""
	Calculates the data for the cumulative case - daily cases chart
	:param case_counts: The case counts in a NumPy array
	:param cumulative_cases: The cumulative cases in a list
	:return: A tuple consisting of the data for the r-value chart:
			cumulative_x: the part of the cumulative cases used as the X axis (cumulative cases > 50) as an integer list
			case_counts_used: the part of the case_counts that is used on the chart as a NumPy array
			exponent_trendline: values for the trendline as a list of floats
			second_wave_x: the cumulative cases in the second wave as a list of ints
			second_wave_trendline: values for the second wave trendline as a list of floats
	"""
	r_rate_start = 0
	for r_rate_start in range(len(cumulative_cases)):
		if cumulative_cases[r_rate_start] >= 50:
			break
	cumulative_x: List[int] = cumulative_cases[r_rate_start::]
	case_counts_used: np.ndarray = case_counts[r_rate_start::]
	rates: List[float] = list((x[0] / x[1] for x in zip(case_counts_used, cumulative_x)))
	avg_rate: float = sum(rates) / len(rates)
	exponent_trendline: List[float] = list(x * avg_rate for x in cumulative_x)
	exponent_trendline_diff: List[float] = list((case_counts_used[i] - exponent_trendline[i]) / cumulative_x[i] for i in range(len(case_counts_used)))
	second_wave_start_idx = np.argmin(exponent_trendline_diff)
	second_wave_x: List[int] = cumulative_x[second_wave_start_idx::]
	second_wave_rates: List[float] = rates[second_wave_start_idx::]
	second_wave_avg_rate: float = sum(second_wave_rates) / len(second_wave_rates)
	second_wave_trendline: List[float] = list(x * second_wave_avg_rate for x in second_wave_x)
	return cumulative_x, case_counts_used, exponent_trendline, second_wave_x, second_wave_trendline


def get_cases_per_day(
		cases: List[CovidCase],
		cutoff_day: datetime.date,
		case_filter: CaseFilter) -> Tuple[
	List[datetime.date],
	np.ndarray,
	Dict[datetime.date, int],
	np.ndarray,
	Dict[datetime.date, int]]:
	"""
	Calculates the cases per day
	:param cases: All cases, List[CovidCase]
	:param cutoff_day: The day after which the cases are ignored, datetime.date
	:param case_filter: The case filter, a CaseFilter
	:return: A Tuple consisting of:
		days: a list of all days with at least one case
		case_counts: a NumPy array with the raw case counts
		cases_per_day: a dictionary of case counts indexed by the days
		death_counts: a NumPy array with the raw death counts
		deaths_per_day: a dictionary of death counts indexed by the days
	"""
	cases_per_day: Dict[datetime.date, int] = dict()
	deaths_per_day: Dict[datetime.date, int] = dict()
	print("Cutoff: {}".format(cutoff_day))
	for c_case in cases:
		if c_case.day > cutoff_day:
			# Skip recent values, those days are most likely incomplete.
			continue
		if not case_filter.filter(c_case):
			continue
		cases_per_day[c_case.day] = cases_per_day.get(c_case.day, 0) + 1
		if c_case.dead:
			deaths_per_day[c_case.day] = deaths_per_day.get(c_case.day, 0) + 1
	days: List[datetime.date] = list(cases_per_day.keys())
	days.sort()
	for day in days:
		if day not in deaths_per_day.keys():
			deaths_per_day[day] = 0
	case_counts: np.ndarray = np.array(tuple(cases_per_day[day] for day in days))
	death_counts: np.ndarray = np.array(tuple(deaths_per_day[day] for day in days))
	return days, case_counts, cases_per_day, death_counts, deaths_per_day


provinces: Tuple[str, ...] = (
	"Groningen",
	"Friesland",
	"Drenthe",
	"Overijssel",
	"Flevoland",
	"Gelderland",
	"Utrecht",
	"Noord-Holland",
	"Zuid-Holland",
	"Zeeland",
	"Noord-Brabant",
	"Limburg")
