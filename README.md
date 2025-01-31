# DockerHub Cleanup Script

## Overview
The **DockerHub Cleanup Script** is a Python-based tool designed to manage and optimize DockerHub storage usage. With DockerHub enforcing a storage limit, this script automates the cleanup of old and unused Docker image tags to ensure compliance while retaining critical assets.

## Key Features:
### 1. Safety First:
- Dry-run mode (--dry-run) previews actions
- Comprehensive CSV report with decision reasons
- Full JSON backup of tag metadata

### 2. Smart Cleanup:
- Maintains latest, prod, production tags
- Keeps 10 most recent tags regardless of name
- Protects tags created in last 7 days
- Skips logspout* (defined) repositories

### 3. Enterprise-Ready:
- Handles Docker Hub pagination
- Rate limiting (1 request/second)
- Error handling for API failures

## Purpose
This tool helps organizations reduce excessive DockerHub storage usage caused by outdated and infrequently accessed images. It ensures adherence to DockerHub's storage limits without compromising critical operations.

## Usage Scenarios
 **Compliance**: Stay within DockerHub's newest storage limit. 50 GB is the case with my Docker Team subscribtion.

**Cost Optimization**: Avoid unnecessary charges for overages.

**Storage Hygiene**: Maintain a clean and organized DockerHub repository.

## Target Audience
The script is tailored for DevOps engineers, platform teams, and organizations utilizing DockerHub for container image storage and distribution.

In my personal opinion, anyone who is already spending way too much on increased pricing of Docker.

### Outputs:
- `cleanup_report.csv` - Detailed audit trail

- `dockerhub_backup.json` - Full tag metadata backup

### Verification Steps:
Run with `--dry-run` and inspect CSV report
Check backup file for completeness
Test on a non-critical repository first!
Monitor Docker Hub storage metrics post-cleanup


## Usage
Generate PAT with read:write privilage here [Docker Settings](https://app.docker.com/settings/personal-access-tokens).

`export DH_TOKEN="your_token"`

`export DH_NAMESPACE="your_organization" `

```
python3 dockerhub_cleanup.py \
  --namespace $DH_NAMESPACE \
  --token $DH_TOKEN \
  --dry-run
  ```