import functools
import urllib.request
import json
from typing import List, Dict, Union
import datetime
import matplotlib.pyplot as plt
import getopt
import sys
import re
import os.path
from progressbar import ProgressBar, Percentage, Bar


class CovidCase:
	
	file_date: datetime = None 
	
	def __init__(
			self,
			Date_statistics: str,
			Agegroup: str,
			Sex: str,
			Province: str,
			Hospital_admission: str,
			Deceased: str
	):
		self.day: datetime.date = datetime.date.fromisoformat(Date_statistics)
		self.age: str = Agegroup
		self.sex: str = Sex
		self.province: str = Province
		self.hospitalized: bool = (Hospital_admission == "Yes")
		self.dead: bool = (Deceased == "Yes")
	
	@staticmethod
	def from_dict(jsondict):
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
	if arg_value in provinces:
		return arg_value
	elif arg_value.lower() == "fryslân":
		return "Friesland"
	else:
		# Case correction and such
		p = re.compile("\\W")
		for province in provinces:
			if p.sub("", province).lower() == p.sub("", arg_value).lower():
				return province
	if province_filter is None:
		print("{} is not a valid Dutch province name.".format(arg_value))
		print("The acceptable values are:")
		print(provinces, sep=", ")
		sys.exit(2)
		
		
def validate_cutoff(arg_value: Union[str, int]) -> int:
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
pbar = ProgressBar(widgets=[Percentage(), Bar()])


def dl_progress(count, blockSize, totalSize):
	global pbar
	pbar.update(int(count * blockSize * 100 / totalSize))
	

def validate_smoothing_window(arg_value: Union[str, int]) -> int:
	try:
		parsed = int(arg_value)
		if parsed < 2 and parsed != 0:
			print("Smoothing window must be greater than 1 or 0 for no smoothing.")
			sys.exit(2)
	except ValueError:
		print("Smoothing window must be an integer. {} is not.".format(arg_value))
		sys.exit(2)
	return parsed


def main(smoothing_window: int, province_filter: Union[str, None], ignore_days: int = 3, force_download: bool = False):
	
	should_download: bool = True
	if not force_download and os.path.isfile(latest_file_location):
		cache_date: datetime = datetime.datetime.fromtimestamp(os.path.getmtime(latest_file_location))
		one_hour_ago = datetime.datetime.now() - datetime.timedelta(hours=1)
		if cache_date > one_hour_ago:
			should_download = False
			
	if should_download:
		print("Downloading most recent data...")
		global pbar
		pbar.start()
		urllib.request.urlretrieve("https://data.rivm.nl/covid-19/COVID-19_casus_landelijk.json", latest_file_location, reporthook=dl_progress)
		print("Data downloaded.")
	else:
		print("File exists in cache as {}, using cached file. Launch the script with -f or --force to force loading the most recent file".format(os.path.abspath(latest_file_location)))
		
	jsondata = json.load(open(latest_file_location))
	cases = list(map(lambda j: CovidCase.from_dict(j), jsondata))
	# Get cases per day
	# I would do something saner in a sane programming language, but alas...
	cases_per_day: Dict[datetime.date, int] = dict()
	cutoff_day: datetime.date = CovidCase.file_date.date() - datetime.timedelta(days=ignore_days)
	for ccase in cases:
		if ccase.day > cutoff_day:
			# Skip today's values because they are useless
			continue
		if province_filter is not None and ccase.province != province_filter:
			continue
		cases_per_day[ccase.day] = cases_per_day.get(ccase.day, 0) + 1
	days = list(cases_per_day.keys())
	days.sort()
	for day in days:
		print("Day: {}\tCases:{}".format(day, cases_per_day[day]))
	tuples = sorted(cases_per_day.items())
	keys, values = zip(*tuples)
	plt.subplot(221)
	if smoothing_window != 0:
		smoothed: List[float] = list()
		for day_idx in range(smoothing_window, len(days) + 1, 1):
			case_sum = 0
			for window in range(day_idx - smoothing_window, day_idx, 1):
				case_sum += cases_per_day[days[window]]
			smoothed.append(case_sum / float(smoothing_window))
		plt.plot(keys, values, keys[smoothing_window - 1::], smoothed)
		plt.title("Daily cases and trend (smoothing window: {})".format(smoothing_window))
	else:
		plt.plot(keys, values)
		plt.title("Daily cases")
	plt.xlabel("Date")
	plt.xticks(rotation="vertical")
	plt.ylabel("Cases")
	cumulative: List[float] = list()
	cumulative.append(values[0])
	for day in days[1::]:
		cumulative.append(cumulative[-1] + cases_per_day[day])
	plt.subplot(222)
	plt.plot(keys, cumulative)
	plt.yscale("log")
	plt.title("Cumulative cases (log)")
	plt.xlabel("Date")
	plt.ylabel("Cumulative cases (log)")
	plt.xticks(rotation="vertical")
	plt.subplot(212)
	plt.plot(cumulative, values)
	plt.xscale("log")
	plt.yscale("log")
	plt.title("Daily cases by cumulative cases (log-log), ~R-value")
	plt.xlabel("Cumulative cases")
	plt.ylabel("Daily cases")
	plt.gcf().canvas.set_window_title("Covid 19 in " + ("the whole Netherlands" if province_filter is None else province_filter))
	plt.subplots_adjust(hspace=1, wspace=0.3)
	plt.show()


def print_help():
	print("Usage: covidstats.py [(-w|--window) <trend smoothing window>] [(-p|--province) <province>] [(-c|--cutoff) <cutoff days>] [(-f|--force)]")


if __name__ == "__main__":
	
	smoothing_window = 0
	province_filter = None
	force_download = False
	cutoff_days = 3
	
	try:
		options, trailing_args = getopt.getopt(sys.argv[1:], "hfw:p:c:", ["force", "window=", "province=", "cutoff="])
		for option, value in options:
			if option == "-h":
				print_help()
				sys.exit()
			elif option in ("-w", "--window"):
				smoothing_window = validate_smoothing_window(value)
			elif option in ("-p", "--province"):
				province_filter = validate_province(value)
			elif option in ("-c", "--cutoff"):
				cutoff_days = validate_cutoff(value)
			elif option in ("-f", "--force"):
				force_download = True
	except getopt.GetoptError:
		print_help()
		sys.exit(2)
	
	main(smoothing_window, province_filter, cutoff_days, force_download)
