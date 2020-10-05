import datetime
from typing import List, Tuple

import numpy as np
from matplotlib import pyplot as plt, ticker as ticker

from covidnl.stats import calculate_smoothed_trends


def plot_daily_cases(days: List[datetime.date], case_counts: np.ndarray, death_counts: np.ndarray, smoothing_window: int):
	plt.plot(days, case_counts, label="Daily cases")
	plt.plot(days, death_counts, label="Of them dead")
	if smoothing_window != 0:
		smoothed_cases, smoothed_deaths = calculate_smoothed_trends(case_counts, death_counts, smoothing_window)
		plt.plot(days, smoothed_cases, label="Trend ({} day avg.)".format(smoothing_window))
		plt.plot(days, smoothed_deaths, label="Death trend ({} day avg.)".format(smoothing_window))
		plt.title("Daily cases and trend (smoothing window: {})".format(smoothing_window))
	else:
		plt.title("Daily cases")


def plot_stacked_cases(days: List[datetime.date], stacked_cases_per_day: np.ndarray, stack_labels: Tuple, stack_by: str):
	plt.stackplot(days, stacked_cases_per_day, labels=stack_labels)
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


def plot_cumulative_cases(days, cumulative_cases, cumulative_deaths):
	plt.plot(days, cumulative_cases, label="Cases")
	plt.plot(days, cumulative_deaths, label="Deaths")
	plt.yscale("log")
	plt.title("Cumulative cases (log)")
	plt.xlabel("Date")
	plt.ylabel("Cumulative cases (log)")
	plt.legend()
	plt.margins(x=0)
