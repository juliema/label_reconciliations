#!/bin/bash

while getopts "v:w:r:e:c:h" option; do
  case "${option}" in
    e) EXPORT=${OPTARG};;
    r) RENAME=${OPTARG};;
    v) VERSION=${OPTARG};;
    w) WORKFLOW=${OPTARG};;
    m) COPYTO=${OPTARG};;
    h) echo "Usage: reconcile.bash -v RECONCILER-VERSION -w WORKFLOW-ID -e EXPORT-FILE-NAME -r RENAME-TO -c COPY-TO"
       exit 1
  esac
done

PREFIX="${WORKFLOW}_${RENAME}"
DIR="output/${PREFIX}"

RAW="${DIR}/${PREFIX}.raw_transcripts.${VERSION}.csv"
RECONCILE="${DIR}/${PREFIX}.reconcile.${VERSION}.csv"
SUMMARY="${DIR}/${PREFIX}.summary.${VERSION}.html"

echo "Workflow:                  ${WORKFLOW}"
echo "Reconciler Version:        v${WORKFLOW}"
echo "Name of Reconciled Folder: ${PREFIX}"

mkdir $DIR

cp $EXPORT $RAW
cp data/NfN_Reconciliation_HelpV1.0.pdf $DIR

python reconcile.py -w $WORKFLOW -r $RECONCILE -s $SUMMARY $RAW

cp $DIR $COPYTO
