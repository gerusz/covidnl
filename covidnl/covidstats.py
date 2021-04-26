import datetime
import json
import os
import sys
from typing import Optional, Tuple, Union

import matplotlib.pyplot as plt

from covidnl.model import CaseFilter, CovidCase
from covidnl.plotting import daily_cases_common, plot_cumulative_cases, plot_daily_cases, plot_r_rate, plot_stacked_cases
from covidnl.runconfig import run_config_from_args, run_config_from_file, RunConfig
from covidnl.stats import calculate_r_estimation, count_cumulative_cases, determine_risk_level, get_cases_per_day, separate_stacks
from covidnl.util import load_cases, validate_date_filter

DEFAULT_JSON_PATH = "config/default.json"


def main(config: RunConfig = RunConfig()):
	"""
	The main function for the stat script. Downloads, processes, and displays the stats.
	:param config: The run configuration
	:return: No return value.
	"""
	
	print("Time: {}".format(datetime.datetime.now()))
	
	cases = load_cases(config.force_download)
	
	cutoff_day, from_day = render_date_filter(config)
	zoom_to = render_zoom(config, cutoff_day)
	
	case_filter = case_filter_from_run_config(config, cutoff_day, from_day)
	
	# Calculate the common stats
	days, case_counts, cases_per_day, death_counts, deaths_per_day, hosp_counts, hosp_per_day = get_cases_per_day(cases, case_filter, config.per_capita)
	cumulative_cases, cumulative_deaths, cumulative_hosp = count_cumulative_cases(days, cases_per_day, deaths_per_day, hosp_per_day)
	risk_level, cases_per_100k, hosp_per_mil = determine_risk_level(case_counts, hosp_counts)
	print("Current risk level: {} (cases/100k last week: {}, hosp./mil last week: {})".format(risk_level, int(cases_per_100k), int(hosp_per_mil)))
	
	# BMH has almost enough colors for the age and the province stacking, and I'm too lazy to make my own palettes, so...
	plt.style.use("bmh")
	
	# Set the window to about 1344 x 864
	plt.figure(figsize=(14, 9), dpi=96)
	
	# Daily cases plot
	plt.subplot(211)  # Span the top half of the window
	if config.stack_by is None:
		plot_daily_cases(days, case_counts, death_counts, hosp_counts, config.smoothing_window, zoom_to)
	else:
		stack_labels, stacked_cases_per_day = separate_stacks(cases, days, config.stack_by, case_filter, config.per_capita)
		plot_stacked_cases(days, stacked_cases_per_day, stack_labels, config.stack_by, zoom_to)
	daily_cases_common(config.per_capita, config.logarithmic)
	
	# Cumulative cases plot
	plt.subplot(223)  # Bottom left
	plot_cumulative_cases(days, cumulative_cases, cumulative_deaths, cumulative_hosp, zoom_to)
	
	# Reproduction rate plot
	plt.subplot(224)  # Bottom right
	r_rates, ignore = calculate_r_estimation(case_counts, config.per_capita)
	r_start_day = days[ignore]
	plot_r_rate(days, r_rates, zoom_to if zoom_to is not None and zoom_to > r_start_day else r_start_day)
	
	# Window data
	plt.get_current_fig_manager().set_window_title("Covid 19 in " + (
			"the whole Netherlands" if case_filter.province_filter is None else case_filter.province_filter))
	plt.subplots_adjust(hspace=0.35, wspace=0.25, left=0.07, right=0.95, top=0.95, bottom=0.09)
	plt.show()


def render_zoom(config: RunConfig, cutoff_day: Optional[datetime.date]) -> datetime.date:
	"""
	Renders the zoom as a datetime.date value
	:param config: The run config containing the zoom parameters
	:param cutoff_day: The cutoff date
	:return: The first date that will be displayed on the charts, as a datetime.date
	"""
	zoom_to: Union[None, datetime.date] = None
	if config.zoom is not None:
		zoom_processed = validate_date_filter(config.zoom, cutoff_day)
		if isinstance(zoom_processed, datetime.date):
			if cutoff_day is not None and zoom_processed > cutoff_day:
				print("Zoom date for stats set after cutoff days, aborting. Pick a date before {}!".format(cutoff_day))
				sys.exit(2)
			zoom_to = zoom_processed
		elif isinstance(zoom_processed, datetime.timedelta):
			zoom_to = cutoff_day - zoom_processed
		if zoom_to is not None:
			print("Showing only dates after {}".format(zoom_to))
	return zoom_to


def render_date_filter(config: RunConfig) -> Tuple[datetime.date, Optional[datetime.date]]:
	"""
	Renders the date filter from the data in the run config
	:param config: The run config
	:return: A tuple containing the cutoff date (always) and the left-cutoff date (optional)
	"""
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
	return cutoff_day, from_day


def case_filter_from_run_config(config: RunConfig, cutoff_day: Optional[datetime.date] = None, from_day: Optional[datetime.date] = None):
	return CaseFilter(config.filter_params.get("province_filter", None), config.filter_params.get("age_filter", None), cutoff_day, from_day)


if __name__ == "__main__":
	
	if len(sys.argv) == 1:
		if os.path.isdir("config") and os.path.isfile(DEFAULT_JSON_PATH):
			run_config = run_config_from_file(DEFAULT_JSON_PATH)
		else:
			if not os.path.isdir("config"):
				print("Config directory doesn't exist. Trying to create it...")
				os.mkdir("config")
			run_config = RunConfig()
			json.dump(run_config.__dict__, open(DEFAULT_JSON_PATH, "w"), indent=1)
			print("Default config written to {}. Running program with those settings...".format(os.path.abspath(DEFAULT_JSON_PATH)))
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
