#!/bin/sh
set -e

# Build the command arguments from the Action inputs.
# GitHub Action inputs are exposed as environment variables with the INPUT_ prefix.
ARGS="--namespace ${INPUT_NAMESPACE} --token ${INPUT_TOKEN}"

# Append optional inputs only if they are provided.
[ -n "${INPUT_SKIP-REPOS}" ] && ARGS="$ARGS --skip-repos ${INPUT_SKIP-REPOS}"
[ -n "${INPUT_PRESERVE}" ] && ARGS="$ARGS --preserve ${INPUT_PRESERVE}"
[ -n "${INPUT_INPUT-JSON}" ] && ARGS="$ARGS --input-json ${INPUT_INPUT-JSON}"
[ -n "${INPUT_REPOS}" ] && ARGS="$ARGS --repos ${INPUT_REPOS}"
[ -n "${INPUT_BACKUP-FILE}" ] && ARGS="$ARGS --backup-file /github/workspace/${INPUT_BACKUP-FILE}"
[ -n "${INPUT_RETENTION-DAYS}" ] && ARGS="$ARGS --retention-days ${INPUT_RETENTION-DAYS}"
[ -n "${INPUT_PRESERVE-LAST}" ] && ARGS="$ARGS --preserve-last ${INPUT_PRESERVE-LAST}"
[ -n "${INPUT_REPORT-FILE}" ] && ARGS="$ARGS --report-file /github/workspace/${INPUT_REPORT-FILE}"

# Append the dry-run flag if enabled.
if [ "${INPUT_DRY-RUN}" = "true" ]; then
  ARGS="$ARGS --dry-run"
fi

echo "Running: python /action/dockerhub_cleanup.py $ARGS"
exec python /action/dockerhub_cleanup.py $ARGS
