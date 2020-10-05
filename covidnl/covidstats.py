import datetime
import getopt
import sys

import matplotlib.pyplot as plt

from covidnl.model import CovidCase, CaseFilter
from covidnl.plotting import plot_daily_cases, plot_stacked_cases, daily_cases_common, plot_r_rate, plot_cumulative_cases
from covidnl.stats import count_cumulative_cases, separate_stacks, calculate_r_rate_data, get_cases_per_day
from covidnl.util import validate_province, validate_cutoff, validate_smoothing_window, validate_stack, load_cases, print_help, validate_age_filter


def main(smoothing_window: int, case_filter: CaseFilter, cutoff_days: int = 3, stack=None, force_download: bool = False):
	"""
	The main function for the stat script. Downloads, processes, and displays the stats.
	:param smoothing_window: The window for the trendline
	:param case_filter: The case filter
	:param cutoff_days: Cutoff days, ignore this many days from the end of the stats
	:param stack: The value to stack the daily trends by.
	:param force_download: Whether the stats have to be downloaded even if they are relatively new.
	:return: No return value.
	"""
	
	cases = load_cases(force_download)
	cutoff_day: datetime.date = CovidCase.file_date.date() - datetime.timedelta(days=cutoff_days)
	
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
	
	try:
		options, trailing_args = getopt.getopt(sys.argv[1:], "hfw:p:c:s:a:", ["help", "force", "window=", "province=", "cutoff=", "stack=", "age="])
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
	
	except getopt.GetoptError:
		print_help()
		sys.exit(2)
	
	if stack_arg == "province" and province_filter_arg is not None:
		print("Can't stack by province with a province filter!")
		sys.exit(2)
	
	main(smoothing_window_arg, CaseFilter(province_filter_arg, age_filter_arg), cutoff_days_arg, stack_arg, force_download_arg)
