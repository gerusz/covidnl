from typing import Union

import covidnl.covidstats
import covidnl.util
from covidnl.model import CaseFilter


def get_stats(smoothing_window: int, province_filter: Union[str, None], ignore_days: int = 3, force_download: bool = False):
	sw = covidnl.util.validate_smoothing_window(smoothing_window)
	prov = covidnl.util.validate_province(province_filter)
	ignore_days = covidnl.util.validate_cutoff(ignore_days)
	covidnl.covidstats.main(sw, CaseFilter(province_filter=prov), force_download=force_download)
