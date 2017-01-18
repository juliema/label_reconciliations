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


# Reconciliation Logic

- Below we describe our logic and process of reconciling multiple transcriptions into a single reconciled transcript for providers. This process is the first order reconciliation logic, the main idea is to capture the label information verbatim and not add any interpretations of the data (e.g. change  rd. to road). This logic is ideal for two reasons, first the instructions for the users is to transcribe the labels as-is and therefore the reconciled transcription should capture that idea. Second, interpretations of these labels could be different from each transcriber  (st. could be street or state) and may require input from the providers about each collection, and may fall under goals for future work. This transcription reconciliation process should be useful across all expeditions regardless of museum origin or taxonomic group covered. 
 
- There are two types of transcription fields, those that include a drop down menu (e.g. Country, State) and those that are free text (e.g. Location and Habitat). We have a different process for reconciling each of these types explained below. The output of the reconciled transcription will include not only the reconciled transcript but also in the ‘summary’ file information about the transcriptions for each category, including the number of completed responses and how well they match for each category (see Figure 1). This will allow providers to determine their level of confidence in each reconciled transcription and check labels that may have been more difficult. For example, if only one transcriber out of three was able to fill in a category, this label is more difficult and providers may choose to check these ones. 

### Controlled Vocabulary Menu Reconciliations:
- The reconciliations for the drop down menu cells are frequency based. In the  reconciled transcript the users will be returned the most frequently selected answer (e.g. if two users selected Arkansas and one selected Alabama the reconciled label will say Arkansas). Providers will be given the most frequently selected response. If there is more than one answer then the most common one will be selected. If there are two conflicting transcripts (one person chose one option and another chose another option) then you will have a “no match” situation. If there is an even split with 4 or more transcripts (two people chose one option and two others another option) then one option is chosen at random. This will only occur if there are 4 (or more) transcripts with two (or more) groups of exact matches..

### Free Text Reconciliations:
- The first step with the reconciliation of the free text fields is to first look for identical labels and again select the most common. If no identical labels are found we first use a normalization step where we remove extra white spaces and punctuation and again look for matches (e.g. ‘M. Denslow’ will be normalized matched to ‘M  Denslow’). 
- Finally we use a fuzzy matching method for comparing the labels. The label selected for the reconciliation will differ depending on the category as indicated below.  The users will again receive information about the number of transcripts and in the case of disagreements between transcripts all possible answers will be given.
- The selected transcription will include the most words with the shortest word length. We want to include all of the words in the transcript, but it seems that generally if people do not write exactly what is on the label that is because they have expanded an abbreviation (e.g. hwy to  highway) therefore we want the label with the shortest length for each word. So the label selected will have the most words but the shortest length of those words.  
- One issue with these categories is that in some cases it is unclear which category the label data should be added to. For example, often it is unclear if data should go in the locality or the habitat field, if a label says ‘middle of a field’, is that locality or habitat information?  Since we don’t legislate how expeditions are setup to capture information, we cannot solve this issue for our providers  Our approach does not move information between categories. Ultimately it will be up to the next level of reconciliation interpretations done by providers to determine if the data are misplaced. 

### Summary of Free - Text Reconciliation process:
    exact match = perfect match between the transcripts
    normalized exact match = removed white spaces and punctuation and then the transcripts matched 
    partial ratio match = parts of words in one transcript are found in anohter (e.g., 'rd' and 'road)
    token set ratio match = the words of one transcript are a subset of another
    no match = nothing matched between the transcripts. This could be because they were completely different or because two were blank whereas only one had a response.    



## What if you need more help?
 - We want to make sure you can use these outputs as efficiently as possible!  We are happy to field questions, explain more to you about all the details, or otherwise make sure you get what you want.  However, we can’t necessarily customize this code in cases where you have a special need.  If you need further customizations, contact us and we can discuss options with you for this effort and how to potentially set up means to cover those costs for our developers.  

 - One thing we are going to be able to help with is converting data to Darwin Core formats.  We are just beginning to build these pipelines, and we hope to have more about that process and how it will work available in Spring 2017. 



