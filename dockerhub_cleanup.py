import argparse
import csv
import json
from datetime import datetime, timedelta
import time
import requests

# DockerHub API configuration
DH_API_BASE = "https://hub.docker.com/v2"

def parse_docker_date(date_str):
    """Parse Docker Hub's timestamp format with variable fractional seconds."""
    date_str = date_str.rstrip("Z")
    if "." in date_str:
        main_part, fractional = date_str.split(".", 1)
        # Pad fractional part to 6 digits (Docker uses 4-6 digits)
        fractional = fractional.ljust(6, "0")[:6]
    else:
        main_part = date_str
        fractional = "000000"
    return datetime.fromisoformat(f"{main_part}.{fractional}")

def parse_args():
    parser = argparse.ArgumentParser(description="Docker Hub Tag Cleanup Script")
    parser.add_argument("--namespace", required=True, help="Docker Hub namespace/organization")
    parser.add_argument("--token", required=True, help="Docker Hub PAT with read:write scope")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without deleting")
    parser.add_argument("--backup-file", default="dockerhub_backup.json", help="Backup file path")
    parser.add_argument("--retention-days", type=int, default=90, help="Days to retain tags")
    parser.add_argument("--preserve-last", type=int, default=10, help="Number of newest tags to preserve")
    parser.add_argument("--skip-repos", nargs="+", default=["logspout"],
                        help="List of repository name prefixes to skip (default: logspout)")
    return parser.parse_args()

def get_paginated_results(url, headers, params=None):
    results = []
    while url:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        results.extend(data["results"])
        url = data.get("next")
        time.sleep(1)  # Rate limit protection
    return results

def process_tags(tags, retention_days, preserve_last):
    """
    Process the tags list to compute parsed dates and determine preservation criteria.
    Returns a list of tag dictionaries with additional computed fields.
    """
    pull_cutoff = datetime.utcnow() - timedelta(days=retention_days)
    processed = []
    
    # Parse dates once and build a new collection with computed fields.
    for tag in tags:
        tag_name = tag.get("name")
        last_updated_str = tag.get("last_updated")
        last_updated_dt = parse_docker_date(last_updated_str)
        last_pulled_str = tag.get("last_pulled")
        last_pulled_dt = parse_docker_date(last_pulled_str) if last_pulled_str else None
        
        processed.append({
            "name": tag_name,
            "last_updated_str": last_updated_str,
            "last_updated_dt": last_updated_dt,
            "last_pulled_str": last_pulled_str,
            "last_pulled_dt": last_pulled_dt,
            "original": tag  # Preserve original data for backup
        })
    
    # Sort tags by last_updated_dt (newest first)
    processed.sort(key=lambda x: x["last_updated_dt"], reverse=True)
    
    # Determine preservation flags:
    # Critical names are always preserved.
    critical_names = {"latest", "prod", "production"}
    # Also preserve the top `preserve_last` newest tags.
    top_newest = {tag["name"] for tag in processed[:preserve_last]}
    
    for tag in processed:
        reasons = []
        if tag["name"].lower() in critical_names:
            reasons.append("critical tag")
        if tag["name"] in top_newest:
            reasons.append(f"top {preserve_last} newest tags")
        if tag["last_pulled_dt"] and tag["last_pulled_dt"] >= pull_cutoff:
            reasons.append(f"pulled within retention period ({retention_days} days)")
        
        if reasons:
            tag["status"] = "PRESERVED"
            tag["reason"] = ", ".join(reasons)
        else:
            # Determine deletion reason based on pull history.
            deletion_reasons = []
            if not tag["last_pulled_dt"]:
                deletion_reasons.append("never pulled")
            else:
                deletion_reasons.append(f"not pulled since {pull_cutoff.isoformat()}")
            tag["status"] = "TO DELETE"
            tag["reason"] = ", ".join(deletion_reasons)
    
    return processed

def main():
    args = parse_args()
    headers = {"Authorization": f"Bearer {args.token}"}
    
    # For backup purposes
    backup_data = {}
    
    # CSV logging setup
    with open("cleanup_report.csv", "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Repository", "Tag", "Last Pulled", "Last Updated", "Status", "Reason"])
        
        # Get all repositories
        try:
            repos_url = f"{DH_API_BASE}/repositories/{args.namespace}/"
            repos = get_paginated_results(repos_url, headers)
        except requests.HTTPError:
            repos_url = f"{DH_API_BASE}/users/{args.namespace}/repositories/"
            repos = get_paginated_results(repos_url, headers)
        
        for repo_data in repos:
            repo_name = repo_data["name"]
            # Check if repository name starts with any of the prefixes provided in skip_repos
            if any(repo_name.startswith(prefix) for prefix in args.skip_repos):
                print(f"Skipping repository: {repo_name}")
                continue
            
            # Fetch tags for the repository
            tags_url = f"{DH_API_BASE}/repositories/{args.namespace}/{repo_name}/tags/"
            try:
                tags = get_paginated_results(tags_url, headers)
            except requests.HTTPError as e:
                print(f"Error fetching tags for {repo_name}: {str(e)}")
                continue
            
            backup_data[repo_name] = tags
            
            # Process tags to add computed fields
            processed_tags = process_tags(tags, args.retention_days, args.preserve_last)
            
            for tag in processed_tags:
                writer.writerow([
                    repo_name,
                    tag["name"],
                    tag["last_pulled_str"],
                    tag["last_updated_str"],
                    tag["status"],
                    tag["reason"]
                ])
                
                # Delete candidates if not preserved and not in dry-run mode.
                if tag["status"] == "TO DELETE":
                    if args.dry_run:
                        print(f"[Dry Run] Would delete {repo_name}:{tag['name']}")
                    else:
                        delete_url = f"{DH_API_BASE}/repositories/{args.namespace}/{repo_name}/tags/{tag['name']}/"
                        try:
                            response = requests.delete(delete_url, headers=headers)
                            response.raise_for_status()
                            print(f"Deleted {repo_name}:{tag['name']}")
                            time.sleep(1)  # Rate limit protection
                        except requests.HTTPError as e:
                            print(f"Failed to delete {repo_name}:{tag['name']} - {str(e)}")
    
    # Save backup data to file
    with open(args.backup_file, "w") as f:
        json.dump(backup_data, f, indent=2)
    print(f"Backup saved to {args.backup_file}")

if __name__ == "__main__":
    main()
