import datetime
import getopt
import json
import os.path
import re
import sys
import urllib.request
from typing import List, Dict, Union, Tuple

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from progressbar import ProgressBar, Percentage, Bar

JSON_URL = "https://data.rivm.nl/covid-19/COVID-19_casus_landelijk.json"


class CovidCase:
	"""
	Represents a single registered case
	"""
	
	file_date: datetime = None
	
	def __init__(
			self,
			date_statistics: str,
			age_group: str,
			sex: str,
			province: str,
			hospital_admission: str,
			deceased: str
	):
		self.day: datetime.date = datetime.date.fromisoformat(date_statistics)
		self.age: str = age_group
		self.sex: str = sex
		self.province: str = province
		self.hospitalized: bool = (hospital_admission == "Yes")
		self.dead: bool = (deceased == "Yes")
	
	@staticmethod
	def from_dict(jsondict):
		"""
		Loads the details of this case from a JSON dictionary
		:param jsondict: The JSON dictionary containing the details of the case
		:return: The CovidCase representation of the given case
		"""
		if CovidCase.file_date is None:
			CovidCase.file_date = datetime.datetime.fromisoformat(jsondict["Date_file"])
		return CovidCase(
			jsondict["Date_statistics"],
			jsondict["Agegroup"],
			jsondict["Sex"],
			jsondict["Province"],
			jsondict["Hospital_admission"],
			jsondict["Deceased"]
		)


provinces = (
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


def validate_province(arg_value: str) -> str:
	"""
	Validates a province argument against the list of Dutch provinces.
	:param arg_value: The input value
	:return: The province value. Capitalization is corrected, dashes are added when necessary, etc...
	"""
	if arg_value in provinces:
		return arg_value
	elif arg_value.lower() == "fryslân":
		return "Friesland"
	# Friesland is a special case, since the province has a different official name in its own minority language.
	else:
		# Case correction and such
		p = re.compile("\\W")
		for province in provinces:
			if p.sub("", province).lower() == p.sub("", arg_value).lower():
				return province
	if province_filter_arg is None:
		print("{} is not a valid Dutch province name.".format(arg_value))
		print("The acceptable values are:")
		print(provinces, sep=", ")
		sys.exit(2)


def validate_cutoff(arg_value: Union[str, int]) -> int:
	"""
	Validates a cutoff value. The input must be an integer greater or equal to 0.
	:param arg_value: The input argument
	:return: The argument parsed to an int if it's valid
	"""
	try:
		parsed = int(arg_value)
		if parsed < 0:
			print("Cutoff days must be 0 or greater")
			sys.exit(2)
	except ValueError:
		print("Cutoff days must be an integer. {} is not.".format(arg_value))
		sys.exit(2)
	return parsed


latest_file_location = "latest.json"
progress_bar = ProgressBar(widgets=[Percentage(), Bar()])


def dl_progress(count, block_size, total_size):
	global progress_bar
	progress_bar.update(int(count * block_size * 100 / total_size))


def validate_smoothing_window(arg_value: Union[str, int]) -> int:
	"""
	Validates the smoothing window for the trendline. Allowed values are 0 or integers >=2.
	:param arg_value: The input value
	:return: The input parsed to an int if it's valid
	"""
	try:
		parsed = int(arg_value)
		if parsed < 2 and parsed != 0:
			print("Smoothing window must be greater than 1 or 0 for no smoothing.")
			sys.exit(2)
	except ValueError:
		print("Smoothing window must be an integer. {} is not.".format(arg_value))
		sys.exit(2)
	return parsed


def validate_stack(arg_value: str) -> str:
	"""
	Validates the stack value, returning the literal value with the expected capitalization
	:param arg_value: The input value
	:return: The literal value with the expected capitalization
	"""
	lowercase = arg_value.lower()
	if lowercase in ("sex", "age", "province"):
		return lowercase
	print("Stacking must be done by sex, age, or province! Not {}.".format(arg_value))
	sys.exit(2)


def main(smoothing_window: int, province_filter: Union[str, None], cutoff_days: int = 3, stack=None, force_download: bool = False):
	"""
	The main function for the stat script. Downloads, processes, and displays the stats.
	:param smoothing_window: The window for the trendline
	:param province_filter: The province to look for. None means no filtering.
	:param cutoff_days: Cutoff days, ignore this many days from the end of the stats
	:param stack: The value to stack the daily trends by.
	:param force_download: Whether the stats have to be downloaded even if they are relatively new.
	:return: No return value.
	"""
	should_download: bool = True
	if not force_download and os.path.isfile(latest_file_location):
		cache_date: datetime = datetime.datetime.fromtimestamp(os.path.getmtime(latest_file_location))
		one_hour_ago = datetime.datetime.now() - datetime.timedelta(hours=1)
		if cache_date > one_hour_ago:
			should_download = False
	
	if should_download:
		print("Downloading most recent data...")
		global progress_bar
		progress_bar.start()
		urllib.request.urlretrieve(JSON_URL, latest_file_location, reporthook=dl_progress)
		print("Data downloaded.")
	else:
		print("File exists in cache as {}, using cached file. Launch the script with -f or --force to force loading the most recent file".format(
			os.path.abspath(latest_file_location)))
	
	jsondata = json.load(open(latest_file_location))
	cases = list(map(lambda j: CovidCase.from_dict(j), jsondata))
	
	# Get cases per day
	cases_per_day: Dict[datetime.date, int] = dict()
	deaths_per_day: Dict[datetime.date, int] = dict()
	cutoff_day: datetime.date = CovidCase.file_date.date() - datetime.timedelta(days=cutoff_days)
	for ccase in cases:
		if ccase.day > cutoff_day:
			# Skip recent values, those days are most likely incomplete.
			continue
		if province_filter is not None and ccase.province != province_filter:
			continue
		cases_per_day[ccase.day] = cases_per_day.get(ccase.day, 0) + 1
		if ccase.dead:
			deaths_per_day[ccase.day] = deaths_per_day.get(ccase.day, 0) + 1
	days = list(cases_per_day.keys())
	days.sort()
	for day in days:
		if day not in deaths_per_day.keys():
			deaths_per_day[day] = 0
		print("Day: {}\tCases:{}\tDeaths:{}".format(day, cases_per_day[day], deaths_per_day.get(day)))
	
	case_counts = np.array(tuple(cases_per_day[day] for day in days))
	death_counts = np.array(tuple(deaths_per_day[day] for day in days))
	
	# Get the data lines split by the stacking criterion if it's present
	if stack is not None:
		if stack == "province":
			stack_labels: Union[Tuple, None] = provinces
		elif stack == "sex":
			stack_labels = ("Male", "Female")
		else:
			stack_labels = (
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
		stacked_cases_per_day: Union[np.ndarray, None] = np.zeros((len(stack_labels), len(days)), dtype=int)
		
		for ccase in cases:
			if ccase.day > cutoff_day:
				# Skip recent values, those days are most likely incomplete.
				continue
			if province_filter is not None and ccase.province != province_filter:
				continue
			stack_key = ccase.province if stack == "province" else (ccase.sex if stack == "sex" else ccase.age)
			if stack_key in stack_labels:
				stack_idx = stack_labels.index(stack_key)
				day_idx = days.index(ccase.day)
				stacked_cases_per_day[stack_idx][day_idx] += 1
	
	else:
		stacked_cases_per_day = None
		stack_labels = None
	
	# BMH has almost enough colors for the age and the province stacking, and I'm too lazy to make my own palettes, so...
	plt.style.use("bmh")
	
	# Set the window to about 1344 x 768
	plt.figure(figsize=(14, 8), dpi=96)
	
	# Daily cases plot
	sp = plt.subplot(211)
	if stack is None:
		plt.plot(days, case_counts, label="Daily cases")
		plt.plot(days, death_counts, label="Of them dead")
		if smoothing_window != 0:
			smoothed_cases: np.ndarray = np.zeros(len(days))
			smoothed_deaths: np.ndarray = np.zeros(len(days))
			for day_idx in range(smoothing_window, len(days) + 1):
				case_sum = sum(case_counts[day_idx - smoothing_window:day_idx:])
				death_sum = sum(death_counts[day_idx - smoothing_window:day_idx:])
				
				smoothed_cases[day_idx - 1] = case_sum / smoothing_window
				smoothed_deaths[day_idx - 1] = death_sum / smoothing_window
			plt.plot(days, smoothed_cases, label="Trend ({} day avg.)".format(smoothing_window))
			plt.plot(days, smoothed_deaths, label="Death trend ({} day avg.)".format(smoothing_window))
			plt.title("Daily cases and trend (smoothing window: {})".format(smoothing_window))
		else:
			plt.title("Daily cases")
	else:
		plt.stackplot(days, stacked_cases_per_day, labels=stack_labels)
		plt.title("Daily cases stacked by {}".format(stack))
	plt.xlabel("Date")
	plt.xticks(rotation="vertical")
	sp.xaxis.set_major_locator(ticker.MultipleLocator(7))
	sp.xaxis.set_minor_locator(ticker.AutoMinorLocator(7))
	sp.yaxis.set_major_locator(ticker.MultipleLocator(200))
	sp.yaxis.set_minor_locator(ticker.AutoMinorLocator(4))
	plt.ylabel("Cases")
	plt.legend(loc='upper left')
	plt.margins(x=0)
	
	# Cumulative cases plot
	plt.subplot(223)
	cumulative_cases: List[float] = list()
	cumulative_deaths: List[float] = list()
	cumulative_cases.append(case_counts[0])
	cumulative_deaths.append(0)
	for day in days[1::]:
		cumulative_cases.append(cumulative_cases[-1] + cases_per_day.get(day, 0))  # Again, my world-famous optimism.
		cumulative_deaths.append(cumulative_deaths[-1] + deaths_per_day.get(day, 0))
	plt.plot(days, cumulative_cases, label="Cases")
	plt.plot(days, cumulative_deaths, label="Deaths")
	plt.yscale("log")
	plt.title("Cumulative cases (log)")
	plt.xlabel("Date")
	plt.ylabel("Cumulative cases (log)")
	plt.xticks(rotation=45)
	plt.legend()
	plt.margins(x=0)
	
	# Reproduction rate plot
	plt.subplot(224)
	
	r_rate_start = 0
	for r_rate_start in range(len(cumulative_cases)):
		if cumulative_cases[r_rate_start] >= 50:
			break
	
	cumulative_x: List[float] = cumulative_cases[r_rate_start::]
	used_values: List[float] = case_counts[r_rate_start::]
	rates: List[float] = list((x[0] / x[1] for x in zip(used_values, cumulative_x)))
	
	avg_rate = sum(rates) / len(rates)
	exponent_trendline = list(x * avg_rate for x in cumulative_x)
	
	exponent_trendline_diff = list((used_values[i] - exponent_trendline[i]) / cumulative_x[i] for i in range(len(used_values)))
	# second_wave_start = min(exponent_trendline_diff)
	second_wave_start_idx = np.argmin(exponent_trendline_diff)  # exponent_trendline_diff.index(second_wave_start)
	
	second_wave_x = cumulative_x[second_wave_start_idx::]
	second_wave_rates = rates[second_wave_start_idx::]
	second_wave_avg_rate = sum(second_wave_rates) / len(second_wave_rates)
	second_wave_trendline = list(x * second_wave_avg_rate for x in second_wave_x)
	
	plt.plot(cumulative_x, used_values, label="Rate")
	plt.plot(cumulative_x, exponent_trendline, label="Overall trendline")
	plt.plot(second_wave_x, second_wave_trendline, label="Second wave trendline")
	plt.xscale("log")
	plt.yscale("log")
	plt.title("Daily cases by cumulative cases (log-log), ~R-value")
	plt.xlabel("Cumulative cases")
	plt.ylabel("Daily cases")
	plt.legend()
	plt.margins(x=0)
	
	plt.gcf().canvas.set_window_title("Covid 19 in " + ("the whole Netherlands" if province_filter is None else province_filter))
	plt.subplots_adjust(hspace=0.35, wspace=0.25, left=0.07, right=0.95, top=0.95, bottom=0.07)
	plt.show()


def print_help():
	print(
		"Usage: covidstats.py [(-w|--window) <trend smoothing window>] [(-p|--province) <province>] [(-c|--cutoff) <cutoff days>] [(-s|--stack) (sex|age|province)] [(-f|--force)]")


if __name__ == "__main__":
	
	smoothing_window_arg = 7
	province_filter_arg = None
	force_download_arg = False
	cutoff_days_arg = 3
	stack_arg = None
	
	try:
		options, trailing_args = getopt.getopt(sys.argv[1:], "hfw:p:c:s:", ["help", "force", "window=", "province=", "cutoff=", "stack="])
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
	except getopt.GetoptError:
		print_help()
		sys.exit(2)
	
	if stack_arg == "province" and province_filter_arg is not None:
		print("Can't stack by province with a province filter!")
		sys.exit(2)
	
	main(smoothing_window_arg, province_filter_arg, cutoff_days_arg, stack_arg, force_download_arg)
