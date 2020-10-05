import datetime
import json
import os.path
import re
import sys
import urllib.request
from email import utils as eut
from typing import Union, Tuple
from urllib.error import URLError

from progressbar import ProgressBar, Percentage, Bar

from covidnl.model import CovidCase
from covidnl.stats import provinces

JSON_URL = "https://data.rivm.nl/covid-19/COVID-19_casus_landelijk.json"


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
	# If the program got here, the argument couldn't be matched to any province
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


def load_cases(force_download):
	should_download: bool = True
	if not force_download and os.path.isfile(latest_file_location):
		cache_date: datetime = datetime.datetime.fromtimestamp(os.path.getmtime(latest_file_location), tz=datetime.datetime.now().astimezone().tzinfo)
		request = urllib.request.Request(JSON_URL, method="HEAD")
		last_modified = datetime.datetime.now() - datetime.timedelta(hours=1)  # Create the failsafe "last-modified" object
		try:
			with urllib.request.urlopen(request) as req:
				# print(req.info())
				lastmod_string = req.info()["Last-Modified"]
				last_modified = datetime.datetime(*eut.parsedate(lastmod_string)[:6], tzinfo=datetime.timezone.utc)
				print("Last modified: {}".format(last_modified))
		except URLError:
			print("Couldn't retrieve last-modified date. Using one hour ago...")
		if cache_date > last_modified:
			should_download = False
			print(
				"Most recent version of the file exists in cache as {} modified at {}, using cached file.\n Launch the script with -f or --force to force loading the most recent file".format(
					os.path.abspath(latest_file_location), cache_date))
	if should_download:
		print("Downloading most recent data...")
		global progress_bar
		progress_bar.start()
		urllib.request.urlretrieve(JSON_URL, latest_file_location, reporthook=dl_progress)
		print("Data downloaded.")
	json_data = json.load(open(latest_file_location))
	cases = list(map(lambda j: CovidCase.from_dict(j), json_data))
	return cases


def validate_age_filter(arg_value: str) -> Tuple[int, Union[int, None]]:
	filter_comps = str.split(arg_value, "-")
	try:
		if filter_comps[0] == "90+":
			age_from = 90
		else:
			age_from = int(filter_comps[0])
		if len(filter_comps) > 1:
			if filter_comps[1] == "90+":
				age_to = 90
			else:
				age_to = int(filter_comps[1])
			
			if age_to > 90:
				age_to = 90
		else:
			age_to = None
		if age_to is not None and age_to < age_from:
			raise ValueError
		return age_from, age_to
	except ValueError:
		print("Invalid age filter string: {}".format(arg_value))
		print("Valid filter: <age-from>[-<age-to>] where: ")
		print("\tage-from: an integer >0 or \"90+\",")
		print("\tage-to: an integer >0 or \"90+\" and >= age-from")
		print("Note: the data contains age in ranges of 10. So age-from will be rounded down to the nearest multiple of 10 and age-to will be rounded up\
					to the next k*10-1.")
		sys.exit(2)


def print_help():
	print(
		"Usage: covidstats.py [(-w|--window) <trend smoothing window>] [(-p|--province) <province>] [(-a|--age) <age filter>] [(-c|--cutoff) <cutoff days>] [(-s|--stack) (sex|age|province)] [(-f|--force)]")
