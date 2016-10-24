# Reconcile Notes from Nature Transcripts

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

- The example above was simplified. We are not given the information is such an easy to digest format as shown in the first table. We have to cobble it together from two sources and extract the relevant fields from nested JSON objects. The two sources are the Notes from Nature subject and classifications files. The nested data is extracted automatically. This program will allow you to just output the data in a form similar to the first table.

- Many researchers will want to know how the program determined the "best" match. By default the program will output an explanations file. This file contains a reason for for why each match was chosen. It similar to:

subject_id | Country | Species Name | Location | Collector
---------- | ------- | ------------ | -------- | ---------
1234 | Exact match, 3 of 3 records with 0 blanks | Normalized exact match, 2 of 3 records with 0 blanks | Token set ratio match on 3 records with 0 blanks, score=95 | No text match on 3 records with 1 blank

- By default, we also output a summary report. This shows you how may of each type of matches occurred for each field. It also provides a list of all of the no matches and potentially problematic matches.

### How to Run the Program

This is a python3 script. You may get help with `./reconcile.py --help` or `python3 ./reconcile.py --help`

The easiest way to run the program with the defauts is:
```
./reconcile.py -w WORKFLOW_ID -c INPUT_CLASSIFICATIONS -s INPUT_SUBJECTS
```
```
python3 reconcile.py -c ./notes-from-nature-classifications.csv -s ./notes-from-nature-subjects.csv -w 2554
```
We need, at a minimum, three pieces of information:
- The workflow ID of the work flow you want to extract. Because each workflow is different we currently cannot extract them all at the same time.
- The location of the raw Notes from Nature classifications CSV file.
- The location of the raw Notes from Nature subjects CSV file.
