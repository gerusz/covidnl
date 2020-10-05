import datetime
import sys
from typing import Tuple, Union, List, Callable


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
			print("Information date: " + jsondict["Date_file"])
		return CovidCase(
			jsondict["Date_statistics"],
			jsondict["Agegroup"],
			jsondict["Sex"],
			jsondict["Province"],
			jsondict["Hospital_admission"],
			jsondict["Deceased"]
		)


class CaseFilter:
	ages: Tuple[Tuple[str, int, int], ...] = (
		("0-9", 0, 9),
		("10-19", 10, 19),
		("20-29", 20, 29),
		("30-39", 30, 39),
		("40-49", 40, 49),
		("50-59", 50, 59),
		("60-69", 60, 69),
		("70-79", 70, 79),
		("80-89", 80, 89),
		("90+", 90, 999)
	)
	
	@staticmethod
	def process_age_filter(input_filter: Union[str, Tuple[int, Union[int, None]]]) -> Union[None, Tuple[str, ...]]:
		if input_filter is str:
			filter_comps = str.split(input_filter, "-")
			try:
				if filter_comps[0] == "90+":
					age_from = 90
				else:
					age_from = int(filter_comps[0])
					if age_from > 90:
						age_from = 90
				if len(filter_comps) > 1:
					if filter_comps[1] == "90+":
						age_to = 90
					else:
						age_to = int(filter_comps[1])
						if age_to > 90:
							age_to = 90
				else:
					age_to = None
				if age_to < age_from:
					raise ValueError
			except ValueError:
				print("Invalid age filter string: {}".format(input_filter))
				print("Valid filter: <age-from>[-<age-to>] where: ")
				print("\tage-from: 0-999 or \"90+\",")
				print("\tage-to: 0-999 or \"90+\" and >= age-from")
				print("Note: the data contains age in ranges of 10. So age-from will be rounded down to the nearest multiple of 10 and age-to will be rounded up\
				to the next k*10-1.")
				sys.exit(2)
		else:
			age_from = input_filter[0]
			age_to = input_filter[1]
		first_range_idx = -1
		last_range_idx = -1
		for age_tuple in CaseFilter.ages:
			if age_tuple[1] <= age_from <= age_tuple[2]:
				first_range_idx = CaseFilter.ages.index(age_tuple)
			if age_to is None:
				last_range_idx = first_range_idx
			elif age_tuple[1] <= age_to <= age_tuple[2]:
				last_range_idx = CaseFilter.ages.index(age_tuple)
			if first_range_idx != -1 and last_range_idx != -1:
				break
		age_tuples = CaseFilter.ages[first_range_idx:last_range_idx + 1:]
		return tuple(x[0] for x in age_tuples)
	
	def __init__(self, province_filter: Union[str, None] = None, age_filter: Union[str, Tuple[int, Union[int, None]], None] = None):
		self.province_filter = province_filter
		self.age_filter = CaseFilter.process_age_filter(age_filter) if age_filter is not None else None
		self.filters: List[Callable[[CovidCase], bool], ...] = list()
		if self.province_filter is not None:
			self.filters.append(lambda x: self.province_filter == x.province)
		if self.age_filter is not None:
			self.filters.append(lambda x: x.age in self.age_filter)
	
	def filter(self, c_case: CovidCase) -> bool:
		return all(map(lambda f: f(c_case), self.filters))
