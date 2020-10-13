# What is this?

First of all, this is **NOT MEDICAL ADVICE**. Just something I hacked up because RIVM doesn't publish charts on a daily basis anymore and I'm a bored nerd.

This little tool here downloads the latest Dutch SARS-CoV-2019 stats from RIVM and generates some interesting charts from them.

The charts are:

* Top left: daily new cases, with a trendline (that is on by default and uses a 7-day sliding average) on a linear scale
* Top right: cumulative cases on a logarithmic scale
* Bottom: cumulative cases and daily cases charted on a log-log scale. A downwards trend shows a <1 reproduction rate.

The file is [found here](https://data.rivm.nl/covid-19/COVID-19_casus_landelijk.json). Warning, it's a 30 MB JSON file (that's going to be fatter the more the govt. botches the pandemic response) so try to open it with a sane text editor. (That is, not notepad.)

# How to use it?

covidstats.py can be ran in three ways:

1. No arguments: the launch arguments will be loaded from ./config/default.json if it exists.

    If it doesn't, the file will be created with the default settings (countrywide stats, 7-day cutoff, 7-day smoothing window) and the program will run with those configurations.
2. A single argument not starting with a hyphen: the argument will be interpreted as the config file to be used.

    If the file is a .json file inside the config folder, both "config/" and ".json" are optional.
    Otherwise, an absolute path to the file is required.
    
3. Custom launch config: the app can be launched with multiple arguments, see below. 

The arguments are:

Short argument|Long argument|Field in a config JSON|Value required?|Effect
---|---|---|---|---
-h|--help|n/a|No|Prints this in a more concise format
-f|--force|force|No (boolean in a json)|Forces the script to redownload the data even if it's less than an hour old
-w|--window|smoothing_window|Yes (integer, \>1 or =0)|\>1: introduces a smoothing window and a trendline on the daily case chart (in orange). 0: disables the trendline. Default: 7.
-p|--province|filter_params.province_filter|Yes (a Dutch province, by its Dutch name, see notes)|Filters the data to a certain province. If absent, countrywide stats are shown.
-a|--age|filter_params.age_filter|Yes (an age range)|Filters the results by age. See notes for possible values.
-c|--cutoff|filter_params.cutoff_days|Yes (integer, >=0)|Defines how many days should be cut off from the end. (Data comes in from the provinces with a delay, so the last few days are unreliable.) Default: 3.
-d|--date|filter_params.date_filter|Yes (a period or an ISO date)|Defines the start date, data before this date will be ignored. Caveat: it will probably wreck the R-rate graph. See notes for possible values.
-z|--zoom|zoom|Yes (a period or an ISO date)|Defines the start date of the charts. Still uses data before that for trends, cumulative cases, R-values, etc... See notes for possible values.
-s|--stack|stack_by|Yes (age, sex, or province)|Instead of a simple daily case plot, plots a stacked area chart. Caveats: Smoothing is disabled (so the argument is irrelevant) and province stacking + province filtering doesn't work (for obvious reasons).
-r|--ratio|per_capita|No (boolean in a json)|The numbers will be shown as cases/100 000 person instead of the raw case counts.

### Notes:

#### Provinces:

Dutch name|English name (if not the same)|
---|---
Groningen|
Friesland or Fryslân|
Drenthe|
Overijssel|
Flevoland|
Gelderland|
Utrecht|
Noord-Holland|North-Holland
Zuid-Holland|South-Holland
Zeeland|Zealand
Noord-Brabant|North-Brabant
Limburg|

#### Ages:

Age ranges in the data are given in bands of 10 years, so 0-9, 10-19, and so on to 80-89 and a separate category for 90+.

The possible filter values:

* A single age: will filter the results for the age range containing said value.

    E.g.: `--age 15` will filter the results for the 10-19 range.
* An age range: will filter the results to include the beginning and the end of the range.

    Examples:
    * `--age 10-19` will filter the results for the 10-19 range.
    * `--age 12-17` will also filter the results for the 10-19 range.
    * `--age 10-39` will filter for ranges 10-19, 20-29, and 30-39
    * `--age 15-35` will filter also filter for ranges 10-19, 20-29, and 30-39 
* Anything greater or equal to 90 will designate the 90+ category, as well as "90+"

#### Date filters:

Date filters with the `-d` or `--date` parameter can be given in the following format:

* An ISO date, that is, in the format yyyy-mm-dd. Example: `--date 2020-07-01`
* A time span before the cutoff date, given as an integer and a letter: **y**ear, **m**onth, **w**eek, **d**ay.

    Examples: `-d 3m`, `--date "2 w"`
    
Date spans of x month are interpreted as "From the same day of the month as the cutoff date, x months before" if possible.
If not (e.g. the cutoff date is a 31st but the targeted month only has 28-30 days) then it's the best estimate.

Similarly, year is treated as a span of 365 for every non-leap year and 366 for every leap year between the current day and the same date n years ago.
Leap days are handled, e.g. a `-d 1y` on feb 29 won't crash it.