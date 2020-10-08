import datetime
from typing import List, Tuple, Union

import numpy as np
from matplotlib import pyplot as plt, ticker as ticker

from covidnl.stats import calculate_smoothed_trends


def plot_daily_cases(
		days: List[datetime.date],
		case_counts: np.ndarray,
		death_counts: np.ndarray,
		smoothing_window: int,
		start_date: Union[datetime.date, None] = None):
	start_idx = zoom_start_idx(days, start_date)
	
	plt.plot(days[start_idx::], case_counts[start_idx::], label="Daily cases")
	plt.plot(days[start_idx::], death_counts[start_idx::], label="Of them dead")
	if smoothing_window != 0:
		smoothed_cases, smoothed_deaths = calculate_smoothed_trends(case_counts, death_counts, smoothing_window)
		shift = smoothing_window // 2
		plt.plot(days[start_idx:-shift:], smoothed_cases[start_idx + shift::], label="Trend ({} day avg.)".format(smoothing_window))
		plt.plot(days[start_idx:-shift:], smoothed_deaths[start_idx + shift::], label="Death trend ({} day avg.)".format(smoothing_window))
		plt.title("Daily cases and trend (smoothing window: {})".format(smoothing_window))
	else:
		plt.title("Daily cases")


def zoom_start_idx(days, start_date):
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
		stack_labels: Tuple,
		stack_by: str,
		start_date: Union[datetime.date, None] = None):
	start_idx = zoom_start_idx(days, start_date)
	
	plt.stackplot(days[start_idx::], stacked_cases_per_day[:, start_idx:], labels=stack_labels)
	plt.title("Daily cases stacked by {}".format(stack_by))


def daily_cases_common():
	plt.xlabel("Date")
	plt.xticks(rotation=90)
	x_axis = plt.gcf().axes[0].get_xaxis()
	y_axis = plt.gcf().axes[0].get_yaxis()
	x_axis.set_major_locator(ticker.MultipleLocator(7))
	x_axis.set_minor_locator(ticker.AutoMinorLocator(7))
	y_axis.set_major_locator(ticker.MultipleLocator(200))
	y_axis.set_minor_locator(ticker.AutoMinorLocator(4))
	plt.ylabel("Cases")
	plt.legend(loc='upper left')
	plt.margins(x=0)


def plot_r_rate(case_counts_used, cumulative_x, exponent_trendline, second_wave_trendline, second_wave_x):
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


def plot_cumulative_cases(days, cumulative_cases, cumulative_deaths, start_date: Union[datetime.date, None] = None):
	start_idx = zoom_start_idx(days, start_date)
	
	plt.plot(days[start_idx::], cumulative_cases[start_idx::], label="Cases")
	
	d_death = cumulative_deaths[-1] - cumulative_deaths[start_idx]
	d_case = cumulative_cases[-1] - cumulative_cases[start_idx]
	if d_case / d_death < 250:
		plt.plot(days[start_idx::], cumulative_deaths[start_idx::], label="Deaths")
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
