#!/bin/sh
set -e

# Build the command arguments from the Action inputs.
# GitHub Action inputs are exposed as environment variables with the INPUT_ prefix.
ARGS="--namespace ${INPUT_NAMESPACE} --token ${INPUT_TOKEN}"

# Append optional inputs only if they are provided.
[ -n "${INPUT_SKIP_REPOS}" ] && ARGS="$ARGS --skip-repos ${INPUT_SKIP_REPOS}"
[ -n "${INPUT_PRESERVE}" ] && ARGS="$ARGS --preserve ${INPUT_PRESERVE}"
[ -n "${INPUT_INPUT_JSON}" ] && ARGS="$ARGS --input-json ${INPUT_INPUT_JSON}"
[ -n "${INPUT_REPOS}" ] && ARGS="$ARGS --repos ${INPUT_REPOS}"
[ -n "${INPUT_BACKUP_FILE}" ] && ARGS="$ARGS --backup-file /github/workspace/${INPUT_BACKUP_FILE}"
[ -n "${INPUT_RETENTION_DAYS}" ] && ARGS="$ARGS --retention-days ${INPUT_RETENTION_DAYS}"
[ -n "${INPUT_PRESERVE_LAST}" ] && ARGS="$ARGS --preserve-last ${INPUT_PRESERVE_LAST}"
[ -n "${INPUT_REPORT_FILE}" ] && ARGS="$ARGS --report-file /github/workspace/${INPUT_REPORT_FILE}"

# Append the dry-run flag if enabled.
if [ "${INPUT_DRY_RUN}" = "true" ]; then
  ARGS="$ARGS --dry-run"
fi

echo "Running: python /action/dockerhub_cleanup.py $ARGS"
exec python /action/dockerhub_cleanup.py $ARGS
