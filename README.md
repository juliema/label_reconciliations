# Reconcile Notes from Nature Transcripts [![Build Status](https://travis-ci.org/juliema/label_reconciliations.svg?branch=master)](https://travis-ci.org/juliema/label_reconciliations)

## Installation

- We require python 3.5 or later
- `git clone https://github.com/juliema/label_reconciliations`
- `cd label_reconciliations`
- Optional: `virtualenv venv -p python3`
- Optional: `source venv/bin/activate`
- `pip install -r requirements.txt`

## Examples

You may get program help via:
```
./reconcile.py --help
```

A typical run will look like:
```
./reconcile.py --reconciled data/reconciled.csv --summary data/summary.html data/classifications-from-nfn.csv
```

## Description

reconcile.py takes a group of raw Notes from Nature transcripts for each subject and reconciles them into the "best" values. The strategy and specific rules for doing this are described in [this document](https://docs.google.com/document/d/1DqhWNsy9UAEgkRnIU7VHrdQL4oQzIm2pjrPULGKK21M/edit#heading=h.967a32z3bwbb).

To get an idea of what this program does let's say that we asked three volunteers to transcribe a label with a country, a species name, a location, and a collector. The country is selected from a drop-down list and the species name, location, and collector are free form text fields. If the result of the input is this:

Volunteer | subject_id | Country | Species Name | Location | Collector
--------- | ---------- | ------- | ------------ | -------- | ---------
Jane | 1234 | Canada | Canis lupus | south Lonely Point | Alvin
Jack | 1234 | Canada | Canis lupus | south of Lonely Point | Simon
Jill | 1234 | Canada | Canis loopy | 5 mi. south of Lonely Point| Theodore

We use a set of measures and heuristics to collapse these three transcripts into a single "best" transcript like this.

subject_id | Country | Species Name | Location | Collector
---------- | ------- | ------------ | -------- | ---------
1234 | Canada | Canis lupus | 5 mi. south of Lonely Point | [NO MATCHES]

### Other Program Features

Many researchers will want to know how the program determined the "best" match. You can use the summary file, "--summary", option to see how the matches were chosen. It also provides an indication of all of the no matches and potentially problematic matches.

If you use the "--unreconciled" option, you will output a CSV file of the raw unreconciled data with the data in the JSON objects extracted into columns. This is useful for performing your own analysis on the data.

# Reconciliation Logic

The main idea is to capture the label information verbatim and not add any interpretations of the data. E.g. we do not change change "rd." to "road". We do this for two reasons. First, the instructions for the citizen scientists is to transcribe the labels as-is and therefore the reconciled transcription should reflect that. Second, interpretations of these labels may be different from expedition to expedition. For example, "st." could be "street" or "state" depending on the context. We have attempted to make the transcription reconciliation process useful across all expeditions regardless of the museum origin or the taxonomic group covered.

One issue with label categories is that in some cases it is unclear which category the label data should be added to. For example, often it is unclear if data should go in the locality or the habitat field, if a label says "middle of a field", is that locality or habitat information?  Since we don’t force how expeditions are setup to capture information, we cannot solve this issue for our providers. Our approach does not move information between categories. Ultimately, it will be up to the next level of reconciliation interpretations done by providers to determine if the data are misplaced.

There are a few types of transcription fields, and by far the most commonly used are those that include a drop-down menu (e.g. Country or State) and those that are free text (e.g. Location or Habitat). We have a different process for reconciling each of these types explained in sections below. In addition to the reconciliation output itself you may also get a summary of how the reconciliation was done including the number of completed responses and how well they matched for each category (see Figure 1). This allows providers to determine their level of confidence in each reconciled transcription and check labels that may have been more difficult. For example, if only one transcriber out of three was able to fill in a category, this label is more difficult and providers may choose to check these transcripts.

Note that the reconciliation logic is geared towards having a low number of transcripts. In the single digits range, probably 5 to 3.

### Controlled Vocabulary Reconciliations:

These are values from a drop-down menu select control. The reconciled value is the most frequently selected answer. For example, if two users selected "Arkansas" and one selected "Alabama" the reconciled value will be "Arkansas". In the event that there is a tie we randomly chose one of those options.

### Free Text Reconciliations:

These are values from a text box control. Here we also chose the most commonly selected answer but in this case what that is is more complicated. The algorithm:

1. We space normalize the string. That is, we remove leading and trailing white space and compress all internal white space into single spaces. For example, "M.&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Smith&nbsp;&nbsp;&nbsp;&nbsp;" becomes "M. Smith". Now we look for the most common of these values. In the event that there is a tie we choose the longest string.

1. If that fails we normalize the sting even more by removing punctuation and changing all letters to lowercase. For example, "M. Smith" from above now becomes "m smith". Then we look for the most common of these values. If we find one we don't return this normalized value but the longest space-only normalized value in the group. An example might help, if we have the following: "JRR Tolkien", "J.R.R. Tolkien", and "jrr tolkien" they all normalize to "jrr tolkien". However, the value returned is the longest value, "J.R.R. Tolkien". The idea here is that we want to remove irrelevant characters from the matching process but we also want to keep the text as close to the original as possible. We found that people often skip entering punctuation and change capitalization.

1. Next we start fuzzy matching on the values (See https://github.com/seatgeek/fuzzywuzzy). The first fuzzy match we use is called a "partial ratio match". If we have two strings of differing lengths we are looking for the largest overlap between the two strings and giving them a score based on the length of the overlap along with the lengths of the two strings. If the best match is above a threshold we return the longer string from the match pair. This fuzzy match is analogous to steps 1 and 2.

1. If that fails we perform another fuzzy match called the "token set ratio match". Here we have abandoned word order and are treating the strings as sets of words. The score is based upon set intersection size and the lengths of the strings. If the best token set ratio is above a threshold we return the string with the most words but with the shortest character length. That is, we sort by score, then by the number of words, and then by the string length.

  - So why do we make this seemingly odd choice for this fuzzy match? The token set ratio does not consider the word order and is not analogous to an exact match like the partial ratio match. We want to include all of the words in the transcript but it seems that in general if people do not write exactly what is on the label it is because they have expanded an abbreviation (e.g. hwy to highway) therefore we want the label with the shortest length for each word keeping all of the information but also keeping the transcript as close to the original as possible.

## What if you need more help?

We want to make sure you can use these outputs as efficiently as possible!  We are happy to field questions, explain more to you about all the details, or otherwise make sure you get what you want.  However, we can’t necessarily customize this code in cases where you have a special need.  If you need further customizations, contact us and we can discuss options with you for this effort and how to potentially set up means to cover those costs for our developers.  Alternatively feel free to fork the code and make it your own or improve upon ours!

One thing we are going to be able to help with is converting data to Darwin Core formats.  We are just beginning to build these pipelines, and we hope to have more about that process and how it will work available in Spring 2017.
