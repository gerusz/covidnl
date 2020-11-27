import getopt
import json
import sys
from typing import Optional, Dict, Union, Tuple

from covidnl.util import print_help, validate_smoothing_window, validate_province, validate_cutoff, validate_stack, validate_age_filter


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
			per_capita: bool = False,
			logarithmic: bool = False):
		"""
		Initializes a run config. Can be called without parameters for a default run config.
		:param force_download: Whether the data file needs to be downloaded regardless of the local cache's freshness. Default: False.
		:param province_filter: The province filter. Default: None.
		:param cutoff_days: How many days from the end of the data have to be ignored. Default: 7.
		:param age_filter: The value of the age filter. Default: None.
		:param date_filter_str: The date filter as a string. Default: None
		:param smoothing_window: The window for the trendline smoothing. Default: 7
		:param stack_by: The value to stack the daily trends by. Default: None.
		:param zoom_str: Date zoom for the charts where the X-axis is a date. Default: None.
		:param per_capita: Whether the daily and the total numbers should be displayed per capita. Default: False.
		:param logarithmic: Whether the daily and the total numbers should be displayed logarithmically. Default: False.
		"""
		self.force_download = force_download
		self.filter_params: Dict[str, Union[str, int, Tuple[int, Optional[int]]]] = {"province_filter": province_filter, "age_filter": age_filter,
		                                                                             "date_filter": date_filter_str, "cutoff_days": cutoff_days}
		self.smoothing_window = smoothing_window
		self.stack_by = stack_by
		self.zoom = zoom_str
		self.per_capita = per_capita
		self.logarithmic = logarithmic
	
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
			json_dict.get("per_capita", False),
			json_dict.get("logarithmic", False)
		)


def run_config_from_args(args) -> RunConfig:
	cfg: RunConfig = RunConfig()
	
	try:
		options, trailing_args = getopt.getopt(
			args,
			"hfw:p:c:s:a:d:z:rl",
			["help", "force", "window=", "province=", "cutoff=", "stack=", "age=", "date=", "zoom=", "ratio", "log", "logarithmic"])
		for option, value in options:
			if option in ("-h", "--help"):
				print_help()
				sys.exit()
			elif option in ("-w", "--window"):
				cfg.smoothing_window = validate_smoothing_window(value)
			elif option in ("-p", "--province"):
				cfg.filter_params["province_filter"] = validate_province(value)
			elif option in ("-c", "--cutoff"):
				cfg.filter_params["cutoff_days"] = validate_cutoff(value)
			elif option in ("-f", "--force"):
				cfg.force_download = True
			elif option in ("-s", "--stack"):
				cfg.stack_by = validate_stack(value)
			elif option in ("-a", "--age"):
				cfg.filter_params["age_filter"] = validate_age_filter(value)
			elif option in ("-d", "--date"):
				cfg.filter_params["date_filter"] = value
			elif option in ("-z", "--zoom"):
				cfg.zoom = value
			elif option in ("-r", "--ratio"):
				cfg.per_capita = True
			elif option in ("-l", "--log", "--logarithmic"):
				cfg.logarithmic = True
	
	except getopt.GetoptError:
		print_help()
		sys.exit(2)
	
	validate_cfg(cfg)
	
	return cfg


def validate_cfg(cfg):
	if cfg.stack_by == "province" and cfg.filter_params["province_filter"] is not None:
		print("Can't stack by province with a province filter!")
		sys.exit(2)
	if cfg.per_capita and cfg.stack_by != "province":
		print("The only stacking available in per-capita mode is by province!")
		sys.exit(2)


def run_config_from_file(file_path: str) -> RunConfig:
	json_dict = json.load(open(file_path))
	return RunConfig.from_json(json_dict)
