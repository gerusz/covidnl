# What is this?

First of all, this is **NOT MEDICAL ADVICE**. Just something I hacked up because RIVM doesn't publish charts on a daily basis anymore and I'm a bored nerd.

This little tool here downloads the latest Dutch SARS-CoV-2019 stats from RIVM and generates some interesting charts from them.

The charts are:

* Top left: daily new cases, with a trendline (that is on by default and uses a 7-day sliding average) on a linear scale
* Top right: cumulative cases on a logarithmic scale
* Bottom: cumulative cases and daily cases charted on a log-log scale. A downwards trend shows a <1 reproduction rate.

The file is [found here](https://data.rivm.nl/covid-19/COVID-19_casus_landelijk.json). Warning, it's a 30 MB JSON file (that's going to be fatter the more the govt. botches the pandemic response) so try to open it with a sane text editor. (That is, not notepad.)

# How to use it?

The best way to run it is to run covidstats.py with some launch arguments. They are all optional, by default the data will show countrywide stats excluding the last 3 days, and a trendline with a 7-day smoothing window. The arguments are:

Short argument|Long argument|Value required?|Effect
---|---|---|---
-h|--help|No|Prints this in a more concise format
-f|--force|No|Forces the script to redownload the data even if it's less than an hour old
-w|--window|Yes (integer, \>1 or =0)|\>1: introduces a smoothing window and a trendline on the daily case chart (in orange). 0: disables the trendline. Default: 7.
-p|--province|Yes (a Dutch province, by its Dutch name, see below)|Filters the data to a certain province. If absent, countrywide stats are shown.
-a|--age|Yes (an age range)|Filters the results by age. See notes for possible values.
-c|--cutoff|Yes (integer, >=0)|Defines how many days should be cut off from the end. (Data comes in from the provinces with a delay, so the last few days are unreliable.) Default: 3.
-s|--stack|Yes (age, sex, or province)|Instead of a simple daily case plot, plots a stacked area chart. Caveats: Smoothing is disabled (so the argument is irrelevant) and province stacking + province filtering doesn't work (for obvious reasons).

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

    E.g.: "--age 15" will filter the results for the 10-19 range.
* An age range: will filter the results to include the beginning and the end of the range.

    Examples:
    * "--age 10-19" will filter the results for the 10-19 range.
    * "--age 12-17" will also filter the results for the 10-19 range.
    * "--age 10-39" will filter for ranges 10-19, 20-29, and 30-39
    * "--age 15-35" will filter also filter for ranges 10-19, 20-29, and 30-39 
* Anything greater or equal to 90 will designate the 90+ category, as well as "90+" 