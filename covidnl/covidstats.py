import datetime
import getopt
import sys
from typing import Union, Dict, Any

import matplotlib.pyplot as plt

from covidnl.model import CovidCase, CaseFilter
from covidnl.plotting import plot_daily_cases, plot_stacked_cases, daily_cases_common, plot_r_rate, plot_cumulative_cases
from covidnl.stats import count_cumulative_cases, separate_stacks, calculate_r_rate_data, get_cases_per_day
from covidnl.util import validate_province, validate_cutoff, validate_smoothing_window, validate_stack, load_cases, print_help, validate_age_filter, \
	validate_date_filter


def main(smoothing_window: int, case_filter_params: Dict[str, Any], stack=None, force_download: bool = False):
	"""
	The main function for the stat script. Downloads, processes, and displays the stats.
	:param smoothing_window: The window for the trendline
	:param case_filter_params: The case filter's parameters. Possible values: cutoff_days, date_filter, age_filter, province_filter
	:param stack: The value to stack the daily trends by.
	:param force_download: Whether the stats have to be downloaded even if they are relatively new.
	:return: No return value.
	"""
	
	cases = load_cases(force_download)
	
	cutoff_day: datetime.date = CovidCase.file_date.date() - datetime.timedelta(days=case_filter_params.get("cutoff_days", 0))
	print("Cutoff: {}".format(cutoff_day))
	from_day: Union[None, datetime.date] = None
	date_filter = case_filter_params.get("date_filter", None)
	if isinstance(date_filter, datetime.date):
		if date_filter > cutoff_day:
			print("Start date for stats set after cutoff days, aborting. Pick a date before {}!".format(cutoff_day))
			sys.exit(2)
		from_day = date_filter_arg
	elif isinstance(date_filter, datetime.timedelta):
		from_day = cutoff_day - date_filter
	if from_day is not None:
		print("Showing only results after {}".format(from_day))
	
	case_filter = CaseFilter(case_filter_params.get("province_filter", None), case_filter_params.get("age_filter", None), from_day, cutoff_day)
	
	# Calculate the common stats
	days, case_counts, cases_per_day, death_counts, deaths_per_day = get_cases_per_day(cases, cutoff_day, case_filter)
	cumulative_cases, cumulative_deaths = count_cumulative_cases(days, cases_per_day, deaths_per_day)
	cumulative_x, case_counts_used, exponent_trendline, second_wave_x, second_wave_trendline, = calculate_r_rate_data(case_counts, cumulative_cases)
	
	# BMH has almost enough colors for the age and the province stacking, and I'm too lazy to make my own palettes, so...
	plt.style.use("bmh")
	
	# Set the window to about 1344 x 864
	plt.figure(figsize=(14, 9), dpi=96)
	
	# Daily cases plot
	plt.subplot(211)
	if stack is None:
		plot_daily_cases(days, case_counts, death_counts, smoothing_window)
	else:
		stack_labels, stacked_cases_per_day = separate_stacks(cases, days, cutoff_day, stack, case_filter)
		plot_stacked_cases(days, stacked_cases_per_day, stack_labels, stack)
	daily_cases_common()
	
	# Cumulative cases plot
	plt.subplot(223)
	plot_cumulative_cases(days, cumulative_cases, cumulative_deaths)
	
	# Reproduction rate plot
	plt.subplot(224)
	plot_r_rate(case_counts_used, cumulative_x, exponent_trendline, second_wave_trendline, second_wave_x)
	plt.gcf().canvas.set_window_title("Covid 19 in " + ("the whole Netherlands" if case_filter.province_filter is None else case_filter.province_filter))
	plt.subplots_adjust(hspace=0.35, wspace=0.25, left=0.07, right=0.95, top=0.95, bottom=0.07)
	plt.show()


if __name__ == "__main__":
	
	smoothing_window_arg = 7
	province_filter_arg = None
	force_download_arg = False
	cutoff_days_arg = 3
	stack_arg = None
	age_filter_arg = None
	date_filter_arg: Union[datetime.date, datetime.timedelta, None] = None
	
	try:
		options, trailing_args = getopt.getopt(sys.argv[1:], "hfw:p:c:s:a:d:", ["help", "force", "window=", "province=", "cutoff=", "stack=", "age=", "date="])
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
				date_filter_arg = validate_date_filter(value)
	
	except getopt.GetoptError:
		print_help()
		sys.exit(2)
	
	if stack_arg == "province" and province_filter_arg is not None:
		print("Can't stack by province with a province filter!")
		sys.exit(2)
	
	main(
		smoothing_window_arg,
		{"province_filter": province_filter_arg, "age_filter": age_filter_arg, "date_filter": date_filter_arg, "cutoff_days": cutoff_days_arg},
		stack_arg,
		force_download_arg)
