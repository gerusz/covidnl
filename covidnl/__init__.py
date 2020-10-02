from typing import Union

import covidnl.covidstats


def get_stats(smoothing_window: int, province_filter: Union[str, None], ignore_days: int = 3, force_download: bool = False):
	sw = covidnl.covidstats.validate_smoothing_window(smoothing_window)
	prov = covidnl.covidstats.validate_province(province_filter)
	ignore_days = covidnl.covidstats.validate_cutoff(ignore_days)
	covidnl.covidstats.main(sw, prov, ignore_days, force_download=force_download)
