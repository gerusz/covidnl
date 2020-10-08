import datetime
import getopt
import sys
from typing import Union, Dict, Any

import matplotlib.pyplot as plt

from covidnl.model import CovidCase, CaseFilter
from covidnl.plotting import plot_daily_cases, plot_stacked_cases, daily_cases_common, plot_cumulative_cases, plot_r_rate
from covidnl.stats import count_cumulative_cases, separate_stacks, get_cases_per_day, calculate_r_estimation
from covidnl.util import validate_province, validate_cutoff, validate_smoothing_window, validate_stack, load_cases, print_help, validate_age_filter, \
	validate_date_filter


def main(smoothing_window: int, case_filter_params: Dict[str, Any], stack=None, force_download: bool = False, zoom: Union[str, None] = None):
	"""
	The main function for the stat script. Downloads, processes, and displays the stats.
	:param smoothing_window: The window for the trendline
	:param case_filter_params: The case filter's parameters. Possible values: cutoff_days, date_filter, age_filter, province_filter
	:param stack: The value to stack the daily trends by.
	:param force_download: Whether the stats have to be downloaded even if they are relatively new.
	:param zoom: Date zoom for the charts where the X-axis is a date.
	:return: No return value.
	"""
	
	cases = load_cases(force_download)
	
	cutoff_day: datetime.date = CovidCase.file_date.date() - datetime.timedelta(days=case_filter_params.get("cutoff_days", 0))
	print("Cutoff: {}".format(cutoff_day))
	from_day: Union[None, datetime.date] = None
	date_filter_str = case_filter_params.get("date_filter", None)
	if date_filter_str is not None:
		date_filter = validate_date_filter(date_filter_str, cutoff_day)
		if isinstance(date_filter, datetime.date):
			if date_filter > cutoff_day:
				print("Start date for stats set after cutoff days, aborting. Pick a date before {}!".format(cutoff_day))
				sys.exit(2)
			from_day = date_filter
		elif isinstance(date_filter, datetime.timedelta):
			from_day = cutoff_day - date_filter
		if from_day is not None:
			print("Using only results after {}".format(from_day))
	
	zoom_to: Union[None, datetime.date] = None
	if zoom is not None:
		zoom_processed = validate_date_filter(zoom, cutoff_day)
		if isinstance(zoom_processed, datetime.date):
			if zoom_processed > cutoff_day:
				print("Zoom date for stats set after cutoff days, aborting. Pick a date before {}!".format(cutoff_day))
				sys.exit(2)
			zoom_to = zoom_processed
		elif isinstance(zoom_processed, datetime.timedelta):
			zoom_to = cutoff_day - zoom_processed
		if zoom_to is not None:
			print("Showing only dates after {}".format(zoom_to))
	
	case_filter = CaseFilter(case_filter_params.get("province_filter", None), case_filter_params.get("age_filter", None), from_day, cutoff_day)
	
	# Calculate the common stats
	days, case_counts, cases_per_day, death_counts, deaths_per_day, hosp_counts, hosp_per_day = get_cases_per_day(cases, cutoff_day, case_filter)
	cumulative_cases, cumulative_deaths, cumulative_hosp = count_cumulative_cases(days, cases_per_day, deaths_per_day, hosp_per_day)
	# cumulative_x, case_counts_used, exponent_trendline, second_wave_x, second_wave_trendline, = calculate_r_rate_data_old_style(case_counts, cumulative_cases)
	r_rates = calculate_r_estimation(case_counts)
	
	# BMH has almost enough colors for the age and the province stacking, and I'm too lazy to make my own palettes, so...
	plt.style.use("bmh")
	
	# Set the window to about 1344 x 864
	plt.figure(figsize=(14, 9), dpi=96)
	
	# Daily cases plot
	plt.subplot(211)
	if stack is None:
		plot_daily_cases(days, case_counts, death_counts, hosp_counts, smoothing_window, zoom_to)
	else:
		stack_labels, stacked_cases_per_day = separate_stacks(cases, days, cutoff_day, stack, case_filter)
		plot_stacked_cases(days, stacked_cases_per_day, stack_labels, stack, zoom_to)
	daily_cases_common()
	
	# Cumulative cases plot
	plt.subplot(223)
	plot_cumulative_cases(days, cumulative_cases, cumulative_deaths, cumulative_hosp, zoom_to)
	
	# Reproduction rate plot
	plt.subplot(224)
	# plot_r_rate_old_style(case_counts_used, cumulative_x, exponent_trendline, second_wave_trendline, second_wave_x)
	plot_r_rate(days, r_rates, zoom_to)
	plt.gcf().canvas.set_window_title("Covid 19 in " + ("the whole Netherlands" if case_filter.province_filter is None else case_filter.province_filter))
	plt.subplots_adjust(hspace=0.35, wspace=0.25, left=0.07, right=0.95, top=0.95, bottom=0.09)
	plt.show()


if __name__ == "__main__":
	
	smoothing_window_arg = 7
	province_filter_arg = None
	force_download_arg = False
	cutoff_days_arg = 3
	stack_arg = None
	age_filter_arg = None
	date_filter_arg_str: Union[str, None] = None
	zoom_arg_str: Union[str, None] = None
	
	try:
		options, trailing_args = getopt.getopt(
			sys.argv[1:],
			"hfw:p:c:s:a:d:z:",
			["help", "force", "window=", "province=", "cutoff=", "stack=", "age=", "date=", "zoom="])
		for option, value in options:
			if option in ("-h", "--help"):
				print_help()
				sys.exit()
			elif option in ("-w", "--window"):
				smoothing_window_arg = validate_smoothing_window(value)
			elif option in ("-p", "--province"):
				province_filter_arg = validate_province(value)
			elif option in ("-c", "--cutoff"):
				cutoff_days_arg = validate_cutoff(value)
			elif option in ("-f", "--force"):
				force_download_arg = True
			elif option in ("-s", "--stack"):
				stack_arg = validate_stack(value)
			elif option in ("-a", "--age"):
				age_filter_arg = validate_age_filter(value)
			elif option in ("-d", "--date"):
				date_filter_arg_str = value
			elif option in ("-z", "--zoom"):
				zoom_arg_str = value
	
	except getopt.GetoptError:
		print_help()
		sys.exit(2)
	
	if stack_arg == "province" and province_filter_arg is not None:
		print("Can't stack by province with a province filter!")
		sys.exit(2)
	
	main(
		smoothing_window_arg,
		{"province_filter": province_filter_arg, "age_filter": age_filter_arg, "date_filter": date_filter_arg_str, "cutoff_days": cutoff_days_arg},
		stack_arg,
		force_download_arg,
		zoom_arg_str)
