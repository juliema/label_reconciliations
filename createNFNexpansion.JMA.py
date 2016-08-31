#!/usr/bin/env python
__author__ = 'vmaidel'
import pandas as pd
import numpy as np
import json
from dateutil import parser
import sys
import os

def extractImageURL(subject_json):
    if 'imageURL' in subject_json.values()[0]:
        return subject_json.values()[0]['imageURL']

def extractImageName(subject_json):
    if 'imageName' in subject_json.values()[0]:
        return subject_json.values()[0]['imageName']

def extractsubjectId(subject_json):
    if 'subjectId' in subject_json.values()[0]:
        return subject_json.values()[0]['subjectId']

def extractReferences(subject_json):
    if 'references' in subject_json.values()[0]:
        return subject_json.values()[0]['references']

def extractExpeditionId(subject_json):
    if '#expeditionId' in subject_json.values()[0]:
        return subject_json.values()[0]['#expeditionId']

def extractCatalogNumber(subject_json):
    if '#catalogNumber' in subject_json.values()[0]:
        return subject_json.values()[0]['#catalogNumber']

def extractCollectionCode(subject_json):
    if '#collectionCode' in subject_json.values()[0]:
        return subject_json.values()[0]['#collectionCode']

def extractInstitutionCode(subject_json):
    if '#institutionCode' in subject_json.values()[0]:
        return subject_json.values()[0]['#institutionCode']

def extractGenus(subject_json):
    if 'genus' in subject_json.values()[0]:
        return subject_json.values()[0]['genus']

def extractScientificName(subject_json):
    if 'scientificName' in subject_json.values()[0]:
        return subject_json.values()[0]['scientificName']

### REMOVE THIS
#def extractAnthrax(subject_json):
#    if 'Anthrax sp.' in subject_json.values()[0]:
#        return subject_json.values()[0]['Anthrax sp.']

def extractSubject_id(subject_json):
    return subject_json.keys()[0]
### CHECK THIS
#def extractLocation(locations):
#    return json.loads(locations).values()[0]

def extractStartedAt(metadata_json):
    return parser.parse(metadata_json['started_at']).strftime('%d-%b-%Y %H:%M:%S')

def extractFinishedAt(metadata_json):
    return parser.parse(metadata_json['finished_at']).strftime('%d-%b-%Y %H:%M:%S')

def extendedUserID(row):
    if pd.isnull(row['user_id']):
        extended=row['user_name']
    else:
        extended=row['user_id']
    return extended

def expandNFNClassifications(workflow_id):
    # read the csv files
    print "Reading classifications csv file for NfN..."
    #change the name of the input files if needed:
    #classifications_df=pd.read_csv("notes-from-nature-relaunch-classifications.csv")
    classifications_df=pd.read_csv("notes-from-nature-classifications.csv")
    #subjects_df = pd.read_csv("notes-from-nature-relaunch-subjects.csv")
    subjects_df = pd.read_csv("notes-from-nature-subjects.csv")
   
    #expand only the workflows that we know how to expand
    classifications_df = classifications_df.loc[classifications_df['workflow_id']==workflow_id,:]
    classifications_df['extended_user_id']=classifications_df[['user_name','user_id']].apply(extendedUserID, axis=1)
    classifications_df.drop(['user_name','user_id','user_ip'], axis=1, inplace=True)
    #bring the last column to be the first
    cols = classifications_df.columns.tolist()
    cols = cols[-1:] + cols[:-1]
    classifications_df = classifications_df[cols]

    classifications_df = pd.merge(classifications_df,subjects_df[['subject_id','locations']],how='left',left_on='subject_ids',right_on='subject_id')
    
    #apply a json.loads function on the whole annotations column
    classifications_df['annotation_json']=classifications_df['annotations'].map(lambda x: json.loads(x))

    #apply a json.loads function on the metadata column
    classifications_df['metadata_json']=classifications_df['metadata'].map(lambda x: json.loads(x))

    #apply a json.loads function on the subject_data column
    classifications_df['subject_json']=classifications_df['subject_data'].map(lambda x: json.loads(x))
    
    classifications_df['provider_imageURL']=classifications_df['subject_json'].apply(extractImageURL)
    classifications_df['provider_imageName']=classifications_df['subject_json'].apply(extractImageName)
    classifications_df['subjectId']=classifications_df['subject_json'].apply(extractsubjectId)
    classifications_df['references']=classifications_df['subject_json'].apply(extractReferences)
    classifications_df['expeditionId']=classifications_df['subject_json'].apply(extractExpeditionId)
    classifications_df['catalogNumber']=classifications_df['subject_json'].apply(extractCatalogNumber)
    classifications_df['collectionCode']=classifications_df['subject_json'].apply(extractCollectionCode)
    classifications_df['institutionCode']=classifications_df['subject_json'].apply(extractInstitutionCode)
    classifications_df['genus']=classifications_df['subject_json'].apply(extractGenus)
    classifications_df['scientificName']=classifications_df['subject_json'].apply(extractScientificName)

    ## REMOVE THIS ONE
    #classifications_df['anthrax']=classifications_df['subject_json'].apply(extractAnthrax)

    #get the file name and the URL
    #classifications_df['zooniverse_URL']=classifications_df['locations'].apply(extractLocation)
    classifications_df['classification_started_at']=classifications_df['metadata_json'].apply(extractStartedAt)
    classifications_df['classification_finished_at']=classifications_df['metadata_json'].apply(extractFinishedAt)

    #extract the elements from the annotation json
    for index, row in classifications_df.iterrows():
        for i in row['annotation_json']:
            if type(i['value']) is unicode:
                    #create columns with task names and assign content to the appropriate row
                    classifications_df.loc[index,i['task']+'_value']=i['value']
                    if i.get('task_label',"None")!="None":
                        classifications_df.loc[index,i['task']+'_task_label']=i['task_label']
            if i.get('task_label',"not_combo")=="not_combo":
                if type(i['value']) is list:
                    #create a column for each dropdown value
                    count = 0
                    #iterate over cases where the values are a list
                    for dropdown in i['value']:
                        count+=1
                        classifications_df.loc[index,i['task']+"_select_label"+"_"+str(count)]=dropdown['select_label']
                        if 'option' in dropdown:
                            classifications_df.loc[index,i['task']+"_option"+"_"+str(count)]=dropdown['option']
                        if 'value' in dropdown:
                            classifications_df.loc[index,i['task']+"_value"+"_"+str(count)]=dropdown['value']
                        if 'label' in dropdown:
                            classifications_df.loc[index,i['task']+"_label"+"_"+str(count)]=dropdown['label']
                    
            else:
                if type(i['value']) is list:
                    #create a column for each dropdown value
                    count = 0
                    for dropdown in i['value']:
                        count+=1
                        if type(dropdown['value']) is unicode:
                            classifications_df.loc[index,dropdown['task']+"_value"]=dropdown['value']
                            classifications_df.loc[index,dropdown['task']+"_task_label"]=dropdown['task_label']
                        elif type(dropdown['value']) is list:
                            val_count = 0
                            for val in dropdown['value']:
                                val_count+=1
                                classifications_df.loc[index,dropdown['task']+"_select_label_"+str(val_count)]=val['select_label']
                                if 'option' in val:
                                    classifications_df.loc[index,dropdown['task']+"_option_"+str(val_count)]=val['option']
                                if 'value' in val:
                                    classifications_df.loc[index,dropdown['task']+"_value_"+str(val_count)]=val['value']
                                if 'label' in val:
                                    classifications_df.loc[index,dropdown['task']+"_label_"+str(val_count)]=val['label']

    #delete the unnecessary columns
    classifications_df.drop(['annotation_json','subject_id','locations','metadata_json','subject_json'], axis=1, inplace=True)

    #reordering the columns so that all the elements are grouped in the same task
    original_cols = list(classifications_df.ix[:,0:classifications_df.columns.get_loc('classification_finished_at')+1].columns.values)
    expanded_cols = list(classifications_df.ix[:,classifications_df.columns.get_loc('classification_finished_at')+1:len(classifications_df.columns)].columns.values)

    sorted_cols = sorted(expanded_cols,key=lambda x:int(x[1:].split('_')[0]))

    classifications_df=classifications_df[original_cols+sorted_cols]

    print "The new columns:"
    print classifications_df.columns.values

    #save to csv
    classifications_df.to_csv('expandedNfN_'+str(workflow_id)+'.csv',sep=',',index = False,encoding='utf-8')

#check prompt arguments
if (len(sys.argv) < 2):
    print len(sys.argv)
    print type(sys.argv[1])
    print "Usage: python createNFNexpansion.py workflow_id"
    os._exit(-1)

try:
    workflow_id=int(sys.argv[1])
except:
    print "Workflow_id should be a number..."
    
#run the extraction function
expandNFNClassifications(workflow_id)

