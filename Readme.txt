## This repo  has all the code for taking raw transcript data from Notes From Nature - through reconciliations


Steps:
1. Raw data donwload 'classifications' file
2. createexpandedjsonJMA.py - expands the raw json format

From here Two options:
  ```raw_data_to_providers.ipynb - takes the expanded file to a raw data format for providers```
  
  OR

b. Take it into Reconciliations, there are two reconciliation steps:
      ```reconciliations.ipynb   - reconciles the controlled vocabulary text
      ```fuzzy_matching.ipynb    - reconciles the free text fields
      
    
