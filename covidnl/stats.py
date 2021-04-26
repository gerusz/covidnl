import datetime
from typing import Dict, List, Tuple

import numpy as np

from covidnl.model import CaseFilter, CovidCase

AGE_CATEGORIES = (
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


def calculate_smoothed_trends(
		case_counts: np.ndarray,
		death_counts: np.ndarray,
		hosp_counts: np.ndarray,
		smoothing_window: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
	"""
	Calculates the smoothed trends with the given smoothing window
	:param case_counts: Cases per day
	:param death_counts: Deaths per day
	:param hosp_counts: Hospitalizations per day
	:param smoothing_window: How many days should the smoothing look behind
	:return: A tuple of NumPy arrays: (smoothed_cases, smoothed_deaths)
	"""
	return smooth_data_line(case_counts, smoothing_window), smooth_data_line(death_counts, smoothing_window), smooth_data_line(hosp_counts, smoothing_window)


def smooth_data_line(data_line: np.ndarray, smoothing_window: int) -> np.ndarray:
	"""
	Smooths a data line with the given smoothing window
	:param data_line: The data line as a NumPy array
	:param smoothing_window: The smoothing window, integer
	:return: The smoothed data line as a NumPy array
	"""
	smoothed_data: np.ndarray = np.zeros(len(data_line))
	for day_idx in range(smoothing_window, len(data_line) + 1):
		sum_data = sum(data_line[day_idx - smoothing_window:day_idx:])
		smoothed_data[day_idx - 1] = sum_data / smoothing_window
	
	return smoothed_data


def count_cumulative_cases(
		days: List[datetime.date],
		cases_per_day: Dict[datetime.date, float],
		deaths_per_day: Dict[datetime.date, float],
		hosp_per_day: Dict[datetime.date, float]) -> Tuple[List[float], List[float], List[float]]:
	"""
	Calculates the cumulative cases and deaths
	:param days: The list of days with at least one case or death
	:param cases_per_day: A dictionary of case counts indexed by days
	:param deaths_per_day: A dictionary of death counts indexed by days
	:param hosp_per_day: A dictionary of hospitalization counts indexed by days
	:return: A tuple of lists containing the cumulative cases and cumulative deaths: (cumulative_cases, cumulative_deaths)
	"""
	return cumulate_data(days, cases_per_day), cumulate_data(days, deaths_per_day), cumulate_data(days, hosp_per_day)


def cumulate_data(days: List[datetime.date], data: Dict[datetime.date, float]) -> List[float]:
	cumulative_data: List[int] = list()
	cumulative_data.append(data.get(days[0], 0))
	for day in days[1::]:
		cumulative_data.append(cumulative_data[-1] + data.get(day, 0))  # Again, my world-famous optimism.
	
	return cumulative_data


def separate_stacks(cases: List[CovidCase], days: List[datetime.date], stack: str, case_filter: CaseFilter, per_capita: bool) -> Tuple[
	Tuple[str, ...], np.ndarray]:
	"""
	Returns the data represented as separate data lines by the stacking category
	:param cases: A list of all CovidCase cases
	:param days: A list of days (datetime.date)
	:param stack: The stacking parameter. String, one of "province", "sex", or "age".
	:param case_filter: A CaseFilter object
	:param per_capita: Whether the stacking should be done per-capita or total. Only works with province stacking.
	:return: A tuple consisting of a list of stack labels (strings) and a 2D NumPy array, first dimension: stack, second dimension: day.
	"""
	
	stack_labels = get_stack_labels(case_filter, stack)
	
	stacked_cases_per_day: np.ndarray = np.zeros((len(stack_labels), len(days)), dtype=float)
	
	for c_case in cases:
		if not case_filter.filter(c_case):  # Cutoff day also integrated in the filter
			continue
		assign_case_to_stack(c_case, days, stack, stack_labels, stacked_cases_per_day)
	if per_capita:
		total_population = sum(provinces.values()) / 100000
		for day_idx in range(len(days)):
			normalize_to = sum(stacked_cases_per_day[:, day_idx]) / total_population
			for (p_idx, province) in enumerate(stack_labels):
				stacked_cases_per_day[p_idx, day_idx] = stacked_cases_per_day[p_idx, day_idx] / (provinces[province] / 100000)
			normalization_factor = normalize_to / sum(stacked_cases_per_day[:, day_idx])
			for p_idx in range(len(stack_labels)):
				stacked_cases_per_day[p_idx, day_idx] = stacked_cases_per_day[p_idx, day_idx] * normalization_factor
	
	return stack_labels, stacked_cases_per_day


def get_stack_labels(case_filter, stack):
	if stack == "province":
		province_names = list(provinces.keys())
		province_names.sort(key=lambda prov: provinces.get(prov), reverse=True)
		stack_labels: Tuple[str, ...] = tuple(province_names)
	elif stack == "sex":
		stack_labels = ("Male", "Female")
	else:
		stack_labels = case_filter.age_filter if case_filter.age_filter is not None else AGE_CATEGORIES
	return stack_labels


def assign_case_to_stack(c_case, days, stack, stack_labels, stacked_cases_per_day):
	if stack == "province":
		stack_key = c_case.province
	elif stack == "sex":
		stack_key = c_case.sex
	else:
		stack_key = c_case.age
	if stack_key in stack_labels:
		stack_idx = stack_labels.index(stack_key)
		day_idx = days.index(c_case.day)
		stacked_cases_per_day[stack_idx][day_idx] += 1


def calculate_r_estimation(cases: np.ndarray, per_capita: bool) -> Tuple[np.ndarray, int]:
	"""
	Calculates the R-rates and returns both the r-rate data line and an integer describing how many days should be ignored from the beginning
	:param cases: The cases in an array
	:param per_capita: Whether the cases are given as per-capita metrics. Used for the "ignore" calculation
	:return: The R-rates and the days to ignore (=when the fifteen-day average is less than 150)
	"""
	five_day_avg = smooth_data_line(cases, 5)
	fifteen_day_avg = smooth_data_line(cases, 15)
	r_estimates = np.zeros(len(cases))
	total_population = sum(provinces.values()) / 100000 if per_capita else 1
	
	ignore = 15
	for idx in range(15, len(fifteen_day_avg)):
		if fifteen_day_avg[ignore] >= 150 / total_population:
			ignore = idx
			break
	
	for day_idx in range(15, len(cases), 1):
		r_estimates[day_idx] = five_day_avg[day_idx] / fifteen_day_avg[day_idx]
	
	return smooth_data_line(r_estimates, 5), ignore


def calculate_r_rate_data_old_style(case_counts: np.ndarray, cumulative_cases: List[int]) -> Tuple[List[int], np.ndarray, List[float], List[int], List[float]]:
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


def get_cases_per_day(cases: List[CovidCase], case_filter: CaseFilter, per_capita: bool) -> Tuple[
	List[datetime.date],
	np.ndarray,
	Dict[datetime.date, int],
	np.ndarray,
	Dict[datetime.date, int],
	np.ndarray,
	Dict[datetime.date, int]]:
	"""
	Calculates the cases per day
	:param cases: All cases, List[CovidCase]
	:param case_filter: The case filter, a CaseFilter
	:param per_capita: Whether the results should be counted per 100k person.
	:return: A Tuple consisting of:
		days: a list of all days with at least one case
		case_counts: a NumPy array with the raw case counts
		cases_per_day: a dictionary of case counts indexed by the days
		death_counts: a NumPy array with the raw death counts
		deaths_per_day: a dictionary of death counts indexed by the days
		hosp_counts: a NumPy array with the raw hospitalization counts
		hosp_per_day: a dictionary of death counts indexed by the days
	"""
	total_population = sum(provinces.values()) / 100000 if per_capita else 1
	cases_per_day: Dict[datetime.date, int] = dict()
	deaths_per_day: Dict[datetime.date, int] = dict()
	hosp_per_day: Dict[datetime.date, int] = dict()
	for c_case in cases:
		if not case_filter.filter(c_case):  # Cutoff day also integrated in the filter
			continue
		cases_per_day[c_case.day] = cases_per_day.get(c_case.day, 0) + 1
		if c_case.dead:
			deaths_per_day[c_case.day] = deaths_per_day.get(c_case.day, 0) + 1
		if c_case.hospitalized:
			hosp_per_day[c_case.day] = hosp_per_day.get(c_case.day, 0) + 1
	days: List[datetime.date] = list(cases_per_day.keys())
	days.sort()
	for day in days:
		if day not in deaths_per_day.keys():
			deaths_per_day[day] = 0
		if day not in hosp_per_day.keys():
			hosp_per_day[day] = 0
		cases_per_day[day] /= total_population
		deaths_per_day[day] /= total_population
		hosp_per_day[day] /= total_population
	case_counts: np.ndarray = np.array(tuple(cases_per_day[day] for day in days))
	death_counts: np.ndarray = np.array(tuple(deaths_per_day[day] for day in days))
	hosp_counts: np.ndarray = np.array(tuple(hosp_per_day[day] for day in days))
	return days, case_counts, cases_per_day, death_counts, deaths_per_day, hosp_counts, hosp_per_day


def determine_risk_level(case_counts: np.ndarray, hosp_counts: np.ndarray, cutoff: int = 7) -> Tuple[int, int, int]:
	population = sum(provinces.values()) / 100000
	cases_last_week = sum(case_counts[len(case_counts) - cutoff - 7:len(case_counts) - cutoff])
	cases_per_100k = cases_last_week / population
	level_by_cases = 1
	if cases_per_100k >= 35:
		level_by_cases += 1
	if cases_per_100k >= 100:
		level_by_cases += 1
	if cases_per_100k >= 250:
		level_by_cases += 1
	
	hosp_last_week = sum(hosp_counts[len(hosp_counts) - cutoff - 7:len(hosp_counts) - cutoff])
	hosp_per_mil = (hosp_last_week * 10) / population
	level_by_hosp_pm = 1
	if hosp_per_mil >= 4:
		level_by_hosp_pm += 1
	if hosp_per_mil >= 16:
		level_by_hosp_pm += 1
	if hosp_per_mil >= 27:
		level_by_hosp_pm += 1
	
	level_by_hosp_daily = 1
	examined_period = hosp_counts[len(hosp_counts) - cutoff - 14:len(hosp_counts) - cutoff]
	if any(dh >= 12 for dh in examined_period):
		level_by_hosp_daily += 1
	if any(dh >= 40 for dh in examined_period):
		level_by_hosp_daily += 1
	if any(dh >= 80 for dh in examined_period):
		level_by_hosp_daily += 1
	
	return max(level_by_cases, level_by_hosp_pm, level_by_hosp_daily), cases_per_100k, hosp_per_mil


provinces: Dict[str, int] = {
		"Zuid-Holland" : 3708696,
		"Noord-Holland": 2879527,
		"Noord-Brabant": 2562955,
		"Gelderland"   : 2085952,
		"Utrecht"      : 1354834,
		"Overijssel"   : 1162406,
		"Limburg"      : 1117201,
		"Friesland"    : 649957,
		"Groningen"    : 585866,
		"Drenthe"      : 493682,
		"Flevoland"    : 423021,
		"Zeeland"      : 383488,
		}
