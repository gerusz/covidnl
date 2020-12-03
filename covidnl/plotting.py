import datetime
from typing import List, Tuple, Optional

import numpy as np
from matplotlib import pyplot as plt, ticker as ticker

from covidnl.stats import calculate_smoothed_trends


def plot_daily_cases(
		days: List[datetime.date],
		case_counts: np.ndarray,
		death_counts: np.ndarray,
		hosp_counts: np.ndarray,
		smoothing_window: int,
		start_date: Optional[datetime.date] = None
):
	start_idx = zoom_start_idx(days, start_date)
	
	title = "Daily cases"
	
	if smoothing_window != 0:
		smoothed_cases, smoothed_deaths, smoothed_hosp = calculate_smoothed_trends(case_counts, death_counts, hosp_counts, smoothing_window)
		shift = smoothing_window // 2
		title += " and trend (smoothing window: {})".format(smoothing_window)
	
	plt.title(title)
	
	plt.plot(days[start_idx::], case_counts[start_idx::], label="Cases")
	if smoothing_window != 0:
		# If the above condition is true, the variables are set.
		# noinspection PyUnboundLocalVariable
		plt.plot(days[start_idx:-shift:], smoothed_cases[start_idx + shift::], label="Trend ({} day avg.)".format(smoothing_window))
	
	plt.plot(days[start_idx::], death_counts[start_idx::], label="Deaths")
	if smoothing_window != 0:
		# If the above condition is true, the variables are set.
		# noinspection PyUnboundLocalVariable
		plt.plot(days[start_idx:-shift:], smoothed_deaths[start_idx + shift::], label="Death trend ({} day avg.)".format(smoothing_window))
	
	plt.plot(days[start_idx::], hosp_counts[start_idx::], label="Hospitalizations")
	if smoothing_window != 0:
		# If the above condition is true, the variables are set.
		# noinspection PyUnboundLocalVariable
		plt.plot(days[start_idx:-shift:], smoothed_hosp[start_idx + shift::], label="Hospitalization trend ({} day avg.)".format(smoothing_window))
	print("Daily cases plotted.")


def zoom_start_idx(days: List[datetime.date], start_date: Optional[datetime.date]) -> int:
	start_idx = 0
	if start_date is not None:
		for idx, day in enumerate(days):
			if day >= start_date:
				start_idx = idx
				break
	return start_idx


def plot_stacked_cases(
		days: List[datetime.date],
		stacked_cases_per_day: np.ndarray,
		stack_labels: Tuple[str, ...],
		stack_by: str,
		start_date: Optional[datetime.date] = None):
	start_idx = zoom_start_idx(days, start_date)
	
	plt.stackplot(days[start_idx::], stacked_cases_per_day[:, start_idx:], labels=stack_labels)
	plt.title("Daily cases stacked by {}".format(stack_by))
	print("Stacked cases plotted.")


def daily_cases_common(per_capita: bool = False, logarithmic: bool = False):
	plt.xlabel("Date")
	plt.xticks(rotation=90)
	x_axis = plt.gcf().axes[0].get_xaxis()
	y_axis = plt.gcf().axes[0].get_yaxis()
	x_axis.set_major_locator(ticker.MultipleLocator(7))
	x_axis.set_minor_locator(ticker.AutoMinorLocator(7))
	if per_capita:
		y_axis.set_major_locator(ticker.MultipleLocator(1))
		y_axis.set_minor_locator(ticker.AutoMinorLocator(4))
	else:
		y_axis.set_major_locator(ticker.MultipleLocator(500))
		y_axis.set_minor_locator(ticker.AutoMinorLocator(5))
	if logarithmic:
		plt.yscale("log")
	y_label = "Cases"
	if per_capita:
		y_label += " per capita"
	if logarithmic:
		y_label += " (log)"
	plt.ylabel(y_label)
	plt.legend(loc='upper left')
	plt.margins(x=0, y=0)
	print("Common stuff set for daily cases.")


def plot_r_rate_old_style(case_counts_used, cumulative_x, exponent_trendline, second_wave_trendline, second_wave_x):
	plt.plot(cumulative_x, case_counts_used, label="Rate")
	plt.plot(cumulative_x, exponent_trendline, label="Overall trendline")
	plt.plot(second_wave_x, second_wave_trendline, label="Second wave trendline")
	plt.xscale("log")
	plt.yscale("log")
	plt.title("Daily cases by cumulative cases (log-log), ~R-value")
	plt.xlabel("Cumulative cases")
	plt.ylabel("Daily cases")
	plt.legend()
	plt.margins(x=0)


def plot_r_rate(days: List[datetime.date], r_rates: np.ndarray, start_date: Optional[datetime.date] = None):
	start_idx = max(15, zoom_start_idx(days, start_date))
	mask_above = np.ma.masked_where(r_rates > 1.0, r_rates).max()
	mask_below = np.ma.masked_where(r_rates < 1.0, r_rates).min()
	r_below = np.ma.masked_greater_equal(r_rates, mask_above + 0.025)
	r_above = np.ma.masked_less_equal(r_rates, mask_below - 0.025)
	
	plt.plot(days[start_idx::], r_below[start_idx::], days[start_idx::], r_above[start_idx::])
	plt.xlabel("Date")
	plt.ylabel("Estimated R-rate")
	plt.title("Estimated R-rate by day (5d avg / 15d avg.)")
	plt.margins(x=0)
	plt.xticks(rotation=30)
	x_axis = plt.gcf().axes[2].get_xaxis()
	time_span: datetime.timedelta = days[-1] - days[start_idx]
	major_tick_weekly = (time_span <= datetime.timedelta(days=120))
	x_axis.set_major_locator(ticker.MultipleLocator(7 if major_tick_weekly else 28))
	x_axis.set_minor_locator(ticker.AutoMinorLocator(7 if major_tick_weekly else 4))
	print("R-rate plotted.")


def plot_cumulative_cases(
		days: List[datetime.date],
		cumulative_cases: List[float],
		cumulative_deaths: List[float],
		cumulative_hosp: List[float],
		start_date: Optional[datetime.date] = None):
	start_idx = zoom_start_idx(days, start_date)
	
	plt.plot(days[start_idx::], cumulative_cases[start_idx::], label="Cases")
	
	d_death = cumulative_deaths[-1] - cumulative_deaths[start_idx]
	d_hosp = cumulative_hosp[-1] - cumulative_hosp[start_idx]
	d_case = cumulative_cases[-1] - cumulative_cases[start_idx]
	if d_case / d_death < 250:
		plt.plot(days[start_idx::], cumulative_deaths[start_idx::], label="Deaths")
	if d_case / d_hosp < 250:
		plt.plot(days[start_idx::], cumulative_hosp[start_idx::], label="Hospitalizations")
	plt.yscale("log")
	plt.title("Cumulative cases (log)")
	plt.xlabel("Date")
	plt.ylabel("Cumulative cases (log)")
	x_axis = plt.gcf().axes[1].get_xaxis()
	major_tick_weekly = (days[-1] - days[start_idx] <= datetime.timedelta(days=120))
	x_axis.set_major_locator(ticker.MultipleLocator(7 if major_tick_weekly else 28))
	x_axis.set_minor_locator(ticker.AutoMinorLocator(7 if major_tick_weekly else 4))
	plt.xticks(rotation=30)
	plt.legend()
	plt.margins(x=0)
	print("Cumulative cases plotted.")
