import datetime
import getopt
import json
import os
import sys
from typing import Union, Dict, Optional

import matplotlib.pyplot as plt

from covidnl.model import CovidCase, CaseFilter
from covidnl.plotting import plot_daily_cases, plot_stacked_cases, daily_cases_common, plot_cumulative_cases, plot_r_rate
from covidnl.stats import count_cumulative_cases, separate_stacks, get_cases_per_day, calculate_r_estimation
from covidnl.util import validate_province, validate_cutoff, validate_smoothing_window, validate_stack, load_cases, print_help, validate_age_filter, \
	validate_date_filter


class RunConfig:
	def __init__(
			self,
			force_download: bool = False,
			province_filter: Optional[str] = None,
			cutoff_days: int = 7,
			age_filter: Optional[str] = None,
			date_filter_str: Optional[str] = None,
			smoothing_window: int = 7,
			stack_by: Optional[str] = None,
			zoom_str: Optional[str] = None,
			per_capita: bool = False):
		"""
		Initializes a run config. Can be called without parameters for a default run config.
		:param force_download: Whether the data file needs to be downloaded regardless of the local cache's freshness. Default: False.
		:param province_filter: The province filter. Default: None.
		:param cutoff_days: How many days from the end of the data have to be ignored. Default: 7.
		:param age_filter: The value of the age filter. Default: None.
		:param date_filter_str: The date filter as a string. Default: None
		:param smoothing_window: The window for the trendline smoothing. Default: 7
		:param stack_by: The value to stack the daily trends by. Default: None.
		:param zoom_str: Date zoom for the charts where the X-axis is a date.
		:param per_capita: Whether the daily and the total numbers should be displayed per capita.
		"""
		self.force_download = force_download
		self.filter_params = {"province_filter": province_filter, "age_filter": age_filter, "date_filter": date_filter_str, "cutoff_days": cutoff_days}
		self.smoothing_window = smoothing_window
		self.stack_by = stack_by
		self.zoom = zoom_str
		self.per_capita = per_capita
	
	@staticmethod
	def from_json(json_dict: Dict):
		return RunConfig(
			json_dict.get("force_download", False),
			json_dict.get("filter_params", dict()).get("province_filter", None),
			json_dict.get("filter_params", dict()).get("cutoff_days", 7),
			json_dict.get("filter_params", dict()).get("age_filter", None),
			json_dict.get("filter_params", dict()).get("date_filter", None),
			json_dict.get("smoothing_window", 7),
			json_dict.get("stack_by", None),
			json_dict.get("zoom", None),
			json_dict.get("per_capita", False))


def main(config: RunConfig = RunConfig()):
	"""
	The main function for the stat script. Downloads, processes, and displays the stats.
	
	:return: No return value.
	"""
	
	cases = load_cases(config.force_download)
	
	cutoff_day: datetime.date = CovidCase.file_date.date() - datetime.timedelta(days=config.filter_params.get("cutoff_days", 0))
	print("Cutoff: {}".format(cutoff_day))
	from_day: Union[None, datetime.date] = None
	date_filter_str = config.filter_params.get("date_filter", None)
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
	if config.zoom is not None:
		zoom_processed = validate_date_filter(config.zoom, cutoff_day)
		if isinstance(zoom_processed, datetime.date):
			if zoom_processed > cutoff_day:
				print("Zoom date for stats set after cutoff days, aborting. Pick a date before {}!".format(cutoff_day))
				sys.exit(2)
			zoom_to = zoom_processed
		elif isinstance(zoom_processed, datetime.timedelta):
			zoom_to = cutoff_day - zoom_processed
		if zoom_to is not None:
			print("Showing only dates after {}".format(zoom_to))
	
	case_filter = CaseFilter(config.filter_params.get("province_filter", None), config.filter_params.get("age_filter", None), from_day, cutoff_day)
	
	# Calculate the common stats
	days, case_counts, cases_per_day, death_counts, deaths_per_day, hosp_counts, hosp_per_day = get_cases_per_day(cases, case_filter, config.per_capita)
	cumulative_cases, cumulative_deaths, cumulative_hosp = count_cumulative_cases(days, cases_per_day, deaths_per_day, hosp_per_day)
	# cumulative_x, case_counts_used, exponent_trendline, second_wave_x, second_wave_trendline, = calculate_r_rate_data_old_style(case_counts, cumulative_cases)
	
	# BMH has almost enough colors for the age and the province stacking, and I'm too lazy to make my own palettes, so...
	plt.style.use("bmh")
	
	# Set the window to about 1344 x 864
	plt.figure(figsize=(14, 9), dpi=96)
	
	# Daily cases plot
	plt.subplot(211)
	if config.stack_by is None:
		plot_daily_cases(days, case_counts, death_counts, hosp_counts, config.smoothing_window, zoom_to)
	else:
		stack_labels, stacked_cases_per_day = separate_stacks(cases, days, config.stack_by, case_filter, config.per_capita)
		plot_stacked_cases(days, stacked_cases_per_day, stack_labels, config.stack_by, zoom_to)
	daily_cases_common(config.per_capita)
	
	# Cumulative cases plot
	plt.subplot(223)
	plot_cumulative_cases(days, cumulative_cases, cumulative_deaths, cumulative_hosp, zoom_to)
	
	# Reproduction rate plot
	plt.subplot(224)
	# plot_r_rate_old_style(case_counts_used, cumulative_x, exponent_trendline, second_wave_trendline, second_wave_x)
	r_rates, ignore = calculate_r_estimation(case_counts, config.per_capita)
	r_start_day = days[ignore]
	plot_r_rate(days, r_rates, zoom_to if zoom_to is not None and zoom_to > r_start_day else r_start_day)
	plt.gcf().canvas.set_window_title("Covid 19 in " + ("the whole Netherlands" if case_filter.province_filter is None else case_filter.province_filter))
	plt.subplots_adjust(hspace=0.35, wspace=0.25, left=0.07, right=0.95, top=0.95, bottom=0.09)
	plt.show()


def run_config_from_args(args) -> RunConfig:
	smoothing_window_arg = 7
	province_filter_arg = None
	force_download_arg = False
	cutoff_days_arg = 7
	stack_arg = None
	age_filter_arg = None
	date_filter_arg_str: Union[str, None] = None
	zoom_arg_str: Union[str, None] = None
	per_capita_arg: bool = False
	
	try:
		options, trailing_args = getopt.getopt(
			args,
			"hfw:p:c:s:a:d:z:r",
			["help", "force", "window=", "province=", "cutoff=", "stack=", "age=", "date=", "zoom=", "ratio"])
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
			elif option in ("-r", "--ratio"):
				per_capita_arg = True
	
	except getopt.GetoptError:
		print_help()
		sys.exit(2)
	
	if stack_arg == "province" and province_filter_arg is not None:
		print("Can't stack by province with a province filter!")
		sys.exit(2)
	
	if per_capita_arg and stack_arg != "province":
		print("The only stacking available in per-capita mode is by province!")
		sys.exit(2)
	
	return RunConfig(
		force_download_arg,
		province_filter_arg,
		cutoff_days_arg,
		age_filter_arg,
		date_filter_arg_str,
		smoothing_window_arg,
		stack_arg,
		zoom_arg_str,
		per_capita_arg)


def run_config_from_file(file_path: str) -> RunConfig:
	json_dict = json.load(open(file_path))
	return RunConfig.from_json(json_dict)


if __name__ == "__main__":
	
	if len(sys.argv) == 1:
		if os.path.isdir("config") and os.path.isfile("config/default.json"):
			run_config = run_config_from_file("config/default.json")
		else:
			if not os.path.isdir("config"):
				print("Config directory doesn't exist. Trying to create it...")
				os.mkdir("config")
			run_config = RunConfig()
			json.dump(run_config.__dict__, open("config/default.json", "w"), indent=1)
			print("Default config written to {}. Running program with those settings...".format(os.path.abspath("config/default.json")))
	elif not sys.argv[1].startswith("-"):
		config_path = sys.argv[1]
		if not os.path.isfile(config_path):
			if not config_path.startswith("config"):
				config_path = "config/" + config_path
			if not config_path.endswith(".json"):
				config_path = config_path + ".json"
		run_config = run_config_from_file(config_path)
	else:
		run_config = run_config_from_args(sys.argv[1:])
	
	main(run_config)
