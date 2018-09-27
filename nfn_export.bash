#!/bin/bash

USAGE="Usage: nfn_export.bash -v RECONCILER-VERSION -w WORKFLOW-ID -r RENAME-TO -c COPY-TO -e EXPORT-FILE-NAME"

while getopts "v:w:r:e:c:h" option; do
  case "${option}" in
    e) EXPORT=${OPTARG};;
    r) RENAME=${OPTARG};;
    v) VERSION=${OPTARG};;
    w) WORKFLOW=${OPTARG};;
    c) COPYTO=${OPTARG};;
    h) echo $USAGE
       exit 1
  esac
done

if [ -z $EXPORT ] || [ -z $RENAME ] || [ -z $VERSION ] || [ -z $WORKFLOW ] || [ -z $COPYTO ]
then
  echo "All arguments are required."
  echo $USAGE
  exit 1
fi

PREFIX="${WORKFLOW}_${RENAME}"
DIR="output/${PREFIX}"

RAW="${DIR}/${PREFIX}.raw_transcripts.${VERSION}.csv"
RECONCILE="${DIR}/${PREFIX}.reconcile.${VERSION}.csv"
SUMMARY="${DIR}/${PREFIX}.summary.${VERSION}.html"

echo ""
echo "Workflow:                  ${WORKFLOW}"
echo "Reconciler Version:        v${VERSION}"
echo "Name of Reconciled Folder: ${PREFIX}"
# echo "Reconciled file            ${RECONCILE}"
# echo "Summary file               ${SUMMARY}"
# echo "Raw file                   ${RAW}"
echo ""

mkdir -p $DIR

cp $EXPORT $RAW
cp data/NfN_Reconciliation_HelpV1.0.pdf $DIR

python reconcile.py -w $WORKFLOW -r $RECONCILE -s $SUMMARY $RAW

cp -r $DIR $COPYTO
