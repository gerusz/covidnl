import datetime
import sqlite3
from typing import Dict, List, Tuple

from model import CaseFilter

date_format = "%Y-%m-%d"

cache_location = "cache.db"


def cache_cases(cases: List[Dict[str, str]]):
	con = sqlite3.connect(cache_location)
	print("Creating DB cache...")
	
	# clear the cache
	cur = con.cursor()
	cur.execute("PRAGMA ENCODING=UTF8")
	cur.execute("DROP TABLE IF EXISTS cases")
	cur.execute(
			"CREATE TABLE cases (date DATE NOT NULL, province TEXT NOT NULL, age_group TEXT NOT NULL, sex CHARACTER(1) NOT NULL, case_count INT, death_count INT, PRIMARY KEY(date, province, age_group, sex))")
	con.commit()
	
	# set up the cached values
	table_rows: Dict[Tuple[datetime.date, str, str, str], Tuple[int, int]] = {}
	
	def cache_key(case: Dict[str, str]) -> Tuple[datetime.date, str, str, str]:
		return (
				datetime.date.fromisoformat(case.get("Date_statistics", "")),
				case.get("Province", ""),
				case.get("Agegroup", ""),
				case.get("Sex", "")
				)
	
	def is_dead(case: Dict[str, str]) -> bool:
		return case.get("Deceased", "No") == "Yes"
	
	for c in cases:
		key = cache_key(c)
		current_row = table_rows.get(key, (0, 0, 0))
		new_row = (current_row[0] + 1, current_row[1] + 1 if is_dead(c) else current_row[1])
		table_rows[key] = new_row
	
	print("{} rows will be cached".format(len(table_rows)))
	# insert the values into the cache
	command_format = "INSERT INTO cases VALUES ('{}','{}','{}','{}',{},{})"
	for key in table_rows.keys():
		value = table_rows[key]
		day = key[0].strftime(date_format)
		command = command_format.format(day, key[1], key[2], key[3], value[0], value[1])
		cur.execute(command)
	con.commit()
	con.close()


def filter_to_where(case_filter: CaseFilter) -> str:
	conditions: List[str] = []
	if case_filter.cutoff_date is not None:
		conditions.append("date <= '{}'".format(case_filter.cutoff_date.strftime(date_format)))
	if case_filter.from_date is not None:
		conditions.append("date >= '{}'".format(case_filter.from_date.strftime(date_format)))
	if case_filter.province_filter is not None:
		conditions.append("province LIKE '{}'".format(case_filter.province_filter))
	if case_filter.age_filter is not None:
		age_values = "('" + "','".join(case_filter.age_filter) + "')"
		conditions.append("age IN {}".format(age_values))
	if len(conditions) == 0:
		return ""
	return "WHERE " + " AND ".join(conditions)


def load_cases_per_day(case_filter: CaseFilter) -> Tuple[Dict[datetime.date, int], Dict[datetime.date, int]]:
	condition = filter_to_where(case_filter)
	con = sqlite3.connect(cache_location)
	command = """SELECT date, SUM(case_count) as daily_cases, sum(death_count) as daily_deaths
	FROM cases
	{}
	GROUP BY date
	ORDER BY date;""".format(condition)
	cur = con.cursor()
	cases_per_day: Dict[datetime.date, int] = dict()
	deaths_per_day: Dict[datetime.date, int] = dict()
	for row in cur.execute(command):
		day = datetime.datetime.strptime(row[0], date_format).date()
		cases_per_day[day] = row[1]
		deaths_per_day[day] = row[2]
	
	return cases_per_day, deaths_per_day


def load_cases_per_day_for_stacking(case_filter: CaseFilter, stack: str) -> Tuple[Tuple[str, ...], Dict[datetime.date, Dict[str, int]]]:
	cols = "date, "
	if stack == "age":
		cols += "age_group"
	elif stack == "province":
		cols += "province"
	elif stack == "sex":
		cols += "sex"
	else:
		raise ValueError("{} is not a valid stacking value".format(stack))
	condition = filter_to_where(case_filter)
	command = """SELECT {0}, SUM(case_count) as daily_cases
	FROM cases
	{1}
	GROUP BY {0}
	ORDER BY {0}""".format(cols, condition)
	con = sqlite3.connect(cache_location)
	cur = con.cursor()
	stacked_cases: Dict[datetime.date, Dict[str, int]] = {}
	stack_keys = set()
	for row in cur.execute(command):
		day = datetime.datetime.strptime(row[0], date_format).date()
		stack_key = row[1]
		cases_per_day = row[2]
		if day not in stacked_cases:
			stacked_cases[day] = {}
		stacked_cases[day][stack_key] = cases_per_day
		stack_keys.add(stack_key)
	return tuple(sorted(stack_keys)), stacked_cases
