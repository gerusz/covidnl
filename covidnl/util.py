import datetime
import json
import multiprocessing
import os.path
import re
import sys
from email import utils as eut
from typing import Optional, Tuple, Union

import urllib3
from progressbar import AdaptiveETA, Bar, FileTransferSpeed, Percentage, ProgressBar

from cache import cache_cases
from model import CovidCase
from stats import provinces

JSON_URL = "https://data.rivm.nl/covid-19/COVID-19_casus_landelijk.json"


def validate_province(arg_value: str) -> str:
	"""
	Validates a province argument against the list of Dutch provinces.
	:param arg_value: The input value
	:return: The province value. Capitalization is corrected, dashes are added when necessary, etc...
	"""
	if arg_value in provinces.keys():
		return arg_value
	elif arg_value.lower() == "fryslân":
		return "Friesland"
	# Friesland is a special case, since the province has a different official name in its own minority language.
	else:
		# Case correction and such
		p = re.compile("\\W")
		for province in provinces.keys():
			if p.sub("", province).lower() == p.sub("", arg_value).lower():
				return province
	# If the program got here, the argument couldn't be matched to any province
	print("{} is not a valid Dutch province name.".format(arg_value))
	print("The acceptable values are:")
	print(provinces.keys(), sep=", ")
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
progress_bar: Optional[ProgressBar] = None


def dl_progress(count, block_size, total_size):
	global progress_bar
	if progress_bar is None:
		progress_bar = ProgressBar(widgets=[Percentage(), Bar(), FileTransferSpeed(), AdaptiveETA()], maxval=int(total_size))
		print("Data size: {} MB".format(int(total_size / (1024 * 1024))))
		progress_bar.start()
	progress = count * block_size
	progress_bar.update(progress if progress < total_size else total_size)


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


def iso_date(arg_value: str):
	try:
		return datetime.date.fromisoformat(arg_value)
	except ValueError as err:
		print("Invalid date {}: {}".format(arg_value, err))
		sys.exit(-2)


def validate_date_filter(arg_value: str, relative_to: Union[datetime.date, None] = None) -> Union[datetime.date, datetime.timedelta]:
	date_as_duration = re.compile("(?P<num>[1-9]\\d*)\\s*(?P<unit>[dDwWmMyY])")  # Now that Y there... _that's_ my trademark optimism!
	date_as_iso = re.compile("202\\d-(0[1-9]|1[0-2])-(0[1-9]|[12]\\d|3[01])")
	
	if date_as_iso.match(arg_value):
		return iso_date(arg_value)
	else:
		duration_match = date_as_duration.match(arg_value)
		if duration_match:
			num = int(duration_match.group("num"))
			unit = duration_match.group("unit").lower()
			if relative_to is None:
				relative_to = datetime.date.today()
			if unit == "y":
				return date_filter_as_years(num, relative_to)
			elif unit == "m":
				return date_filter_as_months(num, relative_to)
			elif unit == "w":
				return date_filter_as_weeks(num)
			else:
				return date_filter_as_days(num)
		else:
			print("Invalid start date delta: {}. Start date must be an integer followed by a time unit (y, m, w or d) or an ISO date (yyyy-mm-dd).")
			sys.exit(2)


def date_filter_as_days(num):
	return datetime.timedelta(days=num)


def date_filter_as_weeks(num):
	return datetime.timedelta(weeks=num)


def date_filter_as_months(num, relative_to):
	today_m_zero_indexed = relative_to.month - 1
	if num >= today_m_zero_indexed:
		new_year = relative_to.year - (num // 12 + 1)
		new_month = 13 - (num % 12)
	else:
		new_year = relative_to.year
		new_month = relative_to.month - num
	try:
		return relative_to.replace(year=new_year, month=new_month)
	except ValueError:
		# Issue that this fixes: apparently today's day is greater than the number of days in the target month. (Or the same leap year issue as above.)
		return datetime.timedelta(days=(365.25 / 12) * num)


def date_filter_as_years(num, relative_to):
	new_year = relative_to.year - num
	# Edge case, symbolizing my undying optimism about the pandemic response... see you in 2024, bug that I just prevented
	# You can probably still crash it if you target the year 1900, but that's just stupid.
	if relative_to.month == 2 and relative_to.day == 29 and new_year % 4 > 0:
		return relative_to.replace(year=new_year, day=28)
	return relative_to.replace(year=new_year)


def download_file_if_newer(url: str, location: str, force_download: bool = False) -> bool:
	"""
	Downloads file from the given URL to the given location if the online version was modified before the cached file, there is no cached file, or the download is forced
	:param url: The URL of the file to download
	:param location: The location of the cached file
	:param force_download: Download even if it's newer
	:return: Whether the file was downloaded or not
	"""
	should_download: bool = True
	http = urllib3.PoolManager()
	head = http.request("HEAD", url).info()
	if not force_download and os.path.isfile(location):
		cache_date: datetime = datetime.datetime.fromtimestamp(os.path.getmtime(location), tz=datetime.datetime.now().astimezone().tzinfo)
		last_modified = datetime.datetime.now() - datetime.timedelta(hours=1)  # Create the failsafe "last-modified" object
		try:
			lastmod_string = head["Last-Modified"]
			last_modified = datetime.datetime(*eut.parsedate(lastmod_string)[:6], tzinfo=datetime.timezone.utc)
			last_modified = last_modified.astimezone(datetime.datetime.now().astimezone().tzinfo)
			print("Last modified: {}, {} ago".format(last_modified, datetime.datetime.now().astimezone() - last_modified))
		except urllib3.exceptions.HTTPError:
			print("Couldn't retrieve last-modified date. Using one hour ago...")
		if cache_date > last_modified:
			should_download = False
			print(
					"Most recent version of the file exists in cache as {} modified at {}, using cached file.\n Launch the script with -f or --force to force loading the most recent file".format(
							os.path.abspath(latest_file_location), cache_date))
	if should_download:
		print("Downloading most recent data...")
		content_length = int(head["Content-Length"])
		downloaded = 0
		dl_request = http.request("GET", url, preload_content=False, headers={'Accept-Encoding': 'application/gzip'})
		dl_progress(0, 1, content_length)
		with open(latest_file_location, "wb") as file:
			for chunk in dl_request.stream(1024 * 1024):
				file.write(chunk)
				downloaded += len(chunk)
				dl_progress(downloaded, 1, content_length)
		print()
		dl_request.release_conn()
		print("Data downloaded.")
	return should_download


def load_cases(force_download: bool):
	downloaded = download_file_if_newer(JSON_URL, latest_file_location, force_download)
	try:
		if downloaded:
			print("Loading JSON file (it's {} MB (thanks Markie), be patient.)".format(os.path.getsize(latest_file_location) // (1024 * 1024)))
			json_data = json.load(open(latest_file_location, encoding="utf8"))
			if CovidCase.file_date is None:
				CovidCase.file_date = datetime.datetime.fromisoformat(json_data[0]["Date_file"])
				print("File loaded. Information date: " + json_data[0]["Date_file"] + ". Loading cases...")
			pool = multiprocessing.Pool()
			cases = list(pool.map(CovidCase.from_dict_parallel, json_data))
			print("{} cases loaded.".format(len(cases)))
			# Caching experiment
			cache_cases(cases)
		else:
			CovidCase.file_date = datetime.datetime.fromtimestamp(os.path.getmtime(latest_file_location), tz=datetime.datetime.now().astimezone().tzinfo)
	except json.decoder.JSONDecodeError:
		if not downloaded:
			print("Couldn't decode cached data. Trying to redownload it...")
			load_cases(True)
		else:
			print("Downloaded data invalid. Try again.")
			sys.exit(-2)


def validate_age_filter(arg_value: str) -> Tuple[int, Optional[int]]:
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
			"Usage:\n\t\t covidstats.py [(-w|--window) <trend smoothing window>] [(-p|--province) <province>] [(-a|--age) <age filter>] [(-c|--cutoff) <cutoff days>] [(-d|--date) start date or offset before the cutoff date] [(-z|--zoom) plotting start date or offset before the cutoff date] [(-s|--stack) (sex|age|province)] [(-f|--force)]")
	print("\tOr:\tcovidstats.py config_file (absolute path or filename in the config directory ({}))".format(os.path.abspath("config")))
	print(
			"\tOr:\tcovidstats.py for launching with the configuration in config/default.json if it exists, or the default config if it doesn't (and write the default config to default.json)")
