# Reconcile Notes from Nature Transcripts

## Installation

- We require python 3.4 or later
- `git clone https://github.com/juliema/label_reconciliations`
- `cd label_reconciliations`
- It is recommended that you use a Python virtual environment for this project.
- Optional: `virtualenv venv -p python3`
- Optional: `source venv/bin/activate`
- `pip install -r requirements.txt`

## Examples

You may get program help via:
```
python reconcile.py -h
```

A typical run will look like:
```
python reconcile.py -r data/reconciled.csv -s data/summary.html data/classifications-from-nfn.csv
```

## Description

reconcile.py takes a group of raw Notes from Nature transcripts for each subject and reconciles them into the "best" values. The strategy and specific rules for doing this are described in [this document](https://docs.google.com/document/d/1DqhWNsy9UAEgkRnIU7VHrdQL4oQzIm2pjrPULGKK21M/edit#heading=h.967a32z3bwbb).

To get an idea of what this program does let's say that we asked three volunteers to transcribe a label with a country, a species name, a location, and a collector. The country is selected from a drop-down list and the species name, location, and collector are free form text fields. If the result of the input is like so:

Volunteer | subject_id | Country | Species Name | Location | Collector
--------- | ---------- | ------- | ------------ | -------- | ---------
Jane | 1234 | Canada | Canis lupus | south Lonely Point | Peter
Jack | 1234 | Canada | Canis lupus | south of Lonely Point | Alvin
Jill | 1234 | Canada | Canis loopy | 5 mi. south of Lonely Point|

We use a set of measures and heuristics to collapse these three transcripts into a single best transcript like so.

subject_id | Country | Species Name | Location | Collector
---------- | ------- | ------------ | -------- | ---------
1234 | Canada | Canis lupus | 5 mi. south of Lonely Point | [NO MATCHES]

### Other Program Features

- Many researchers will want to know how the program determined the "best" match. Use the summary file ("-s" option) to see how the matches were chosen. It also provides an indication of all of the no matches and potentially problematic matches.

- Using the "-u" option, You may also output a CSV file of the raw unreconciled data with the data in the JSON objects extracted into columns.
