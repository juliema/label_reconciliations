## This repo  has all the code for taking raw transcript data from Notes From Nature - through reconciliations

https://docs.google.com/document/d/1DqhWNsy9UAEgkRnIU7VHrdQL4oQzIm2pjrPULGKK21M/edit#heading=h.967a32z3bwbb

Steps:
1. Raw data donwload 'classifications' and 'subject' file
2. createexpandedjsonJMA.py - expands the raw json format for a specific workflow

Next Two options:
  a. Create a raw data output for providers with all the transcripts:
      1. raw_data_to_providers.ipynb - takes the expanded file to a raw data format for providers
  OR

b. Do Reconciliations. There are two reconciliation steps:
      1. reconciliations.ipynb   - reconciles the controlled vocabulary text
      2. fuzzy_matching.ipynb    - reconciles the free text fields
      
    
