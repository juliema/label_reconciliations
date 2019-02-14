#!/bin/bash

USAGE=$(cat <<'USAGE_END'

  Usage: nfn_export.bash -v RECONCILER-VERSION -w WORKFLOW-ID -r RENAME-TO -a ARGS -c COPY-TO -e EXPORT-FILE-NAME

  -h
      Print this message and exit.

  -v RECONCILER-VERSION
      The version of reconcile.py. This gets inserted into output file names.

  -w WORKFLOW-ID
      The expedition's workflow ID. This will be prepended to output file names.

  -r RENAME-TO
      The output file names without the RECONCILER-VERSION or WORKFLOW-ID.

  -a ARGS
      Any extra arguments to pass to reconcile.py. If you have many, quote them.

  -c COPY-TO
      Copy the output files to this directory.

  -e EXPORT-FILE-NAME
      The raw input file that reconcile.py uses as input.
.
USAGE_END
)

while getopts "a:v:w:r:e:c:h" option; do
  case "${option}" in
    e) EXPORT=${OPTARG};;
    r) RENAME=${OPTARG};;
    v) VERSION=${OPTARG};;
    w) WORKFLOW=${OPTARG};;
    c) COPYTO=${OPTARG};;
    a) XARGS=${OPTARG};;
    h) echo "$USAGE"
       exit 1
  esac
done

if [ -z $EXPORT ] || [ -z $RENAME ] || [ -z $VERSION ] || [ -z $WORKFLOW ]
then
  echo "Arguments: -v, -w, -r, & -e are required."
  echo "$USAGE"
  exit 1
fi

PREFIX="${WORKFLOW}_${RENAME}"
DIR="output/${PREFIX}"

RAW="${DIR}/${PREFIX}.raw_transcripts.${VERSION}.csv"
RECONCILE="${DIR}/${PREFIX}.reconciled.${VERSION}.csv"
SUMMARY="${DIR}/${PREFIX}.summary.${VERSION}.html"

echo ""
echo "Workflow:                  ${WORKFLOW}"
echo "Reconciler Version:        v${VERSION}"
echo "Name of Reconciled Folder: ${PREFIX}"
# echo "Reconciled file            ${RECONCILE}"
# echo "Summary file               ${SUMMARY}"
# echo "Raw file                   ${RAW}"
# echo "Copy to:                   ${COPYTO}"
echo ""

mkdir -p $DIR

cp $EXPORT $RAW
cp data/NfN_Reconciliation_HelpV1.0.pdf $DIR

python3 reconcile.py $XARGS -w $WORKFLOW -r $RECONCILE -s $SUMMARY $RAW

if [ -n "$COPYTO" ]
then
  cp -r $DIR $COPYTO
fi
