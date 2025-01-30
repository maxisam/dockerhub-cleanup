import argparse
import csv
import json
from datetime import datetime, timedelta
import time
import requests

# DockerHub API configuration
DH_API_BASE = "https://hub.docker.com/v2"

def parse_docker_date(date_str):
    """Parse Docker Hub's timestamp format with variable fractional seconds"""
    # Remove trailing Z if present
    date_str = date_str.rstrip("Z")
    
    # Split into main part and fractional seconds
    if "." in date_str:
        main_part, fractional = date_str.split(".", 1)
        # Pad fractional part to 6 digits (Docker uses 4-6 digits)
        fractional = fractional.ljust(6, "0")[:6]
    else:
        main_part = date_str
        fractional = "000000"
    
    # Rebuild ISO format string
    return datetime.fromisoformat(f"{main_part}.{fractional}")
# I call it user friendly
def parse_args():
    parser = argparse.ArgumentParser(description="Docker Hub Tag Cleanup Script")
    parser.add_argument("--namespace", required=True, help="Docker Hub namespace/organization")
    parser.add_argument("--token", required=True, help="Docker Hub PAT with read:write scope")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without deleting")
    parser.add_argument("--backup-file", default="dockerhub_backup.json", help="Backup file path")
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

def main():
    args = parse_args()
    headers = {"Authorization": f"Bearer {args.token}"}
    
    # Backup storage
    backup_data = {}
    
    # CSV logging setup
    with open("cleanup_report.csv", "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Repository", "Tag", "Last Pulled", "Last Updated", "Status", "Reason"])
        
        # Get all repositories
        repos_url = f"{DH_API_BASE}/repositories/{args.namespace}/"
        repos = get_paginated_results(repos_url, headers)
        
        for repo_data in repos:
            repo_name = repo_data["name"]
            
            # Skip logspout* repositories
            if repo_name.startswith("logspout"):
                print(f"Skipping logspout repository: {repo_name}")
                continue
                
            # Get all tags for repository
            tags_url = f"{DH_API_BASE}/repositories/{args.namespace}/{repo_name}/tags/"
            try:
                tags = get_paginated_results(tags_url, headers)
            except requests.HTTPError as e:
                print(f"Error fetching tags for {repo_name}: {str(e)}")
                continue
                
            backup_data[repo_name] = tags
            preserved_tags = set()
            deletion_candidates = []

            # Sort tags by last_updated (newest first)
            sorted_tags = sorted(tags, key=lambda x: x["last_updated"], reverse=True)
            
            # Identify tags to preserve
            preserved_tags.update(
                tag["name"] for tag in sorted_tags 
                if tag["name"].lower() in {"latest", "prod", "production"}
            )
            
            # Preserve top 10 newest tags
            preserved_tags.update(tag["name"] for tag in sorted_tags[:10])
            
            # Process all tags
            for tag in sorted_tags:
                tag_name = tag["name"]
                last_pulled = tag.get("last_pulled")
                last_updated = parse_docker_date(tag["last_updated"])

                # Calculate time thresholds
                now = datetime.utcnow()
                pull_cutoff = now - timedelta(days=90)
                creation_cutoff = now - timedelta(days=7)
                
                # Preservation check
                if tag_name in preserved_tags:
                    writer.writerow([
                        repo_name,
                        tag_name,
                        last_pulled,
                        tag["last_updated"],
                        "PRESERVED",
                        "Critical tag or top 10 recent"
                    ])
                    continue
                
                # Deletion eligibility check
                delete_reason = []
                if not last_pulled:
                    delete_reason.append("never pulled")
                else:
                    last_pulled_dt = datetime.fromisoformat(last_pulled.rstrip("Z"))
                    if last_pulled_dt < pull_cutoff:
                        delete_reason.append("not pulled in 90 days")
                        
                if last_updated < creation_cutoff:
                    delete_reason.append("older than 7 days")
                else:
                    delete_reason.append("too new to delete")
                
                if "not pulled in 90 days" in delete_reason and "older than 7 days" in delete_reason:
                    deletion_candidates.append(tag)
                    writer.writerow([
                        repo_name,
                        tag_name,
                        last_pulled,
                        tag["last_updated"],
                        "TO DELETE",
                        ", ".join(delete_reason)
                    ])
                else:
                    writer.writerow([
                        repo_name,
                        tag_name,
                        last_pulled,
                        tag["last_updated"],
                        "PRESERVED",
                        ", ".join(delete_reason)
                    ])
            
            # Delete candidates
            for tag in deletion_candidates:
                if args.dry_run:
                    print(f"[Dry Run] Would delete {repo_name}:{tag['name']}")
                    continue
                
                delete_url = f"{DH_API_BASE}/repositories/{args.namespace}/{repo_name}/tags/{tag['name']}/"
                try:
                    response = requests.delete(delete_url, headers=headers)
                    response.raise_for_status()
                    print(f"Deleted {repo_name}:{tag['name']}")
                    time.sleep(1)  # Rate limit protection
                except requests.HTTPError as e:
                    print(f"Failed to delete {repo_name}:{tag['name']} - {str(e)}")
    
    # Save backup
    with open(args.backup_file, "w") as f:
        json.dump(backup_data, f, indent=2)
    print(f"Backup saved to {args.backup_file}")

if __name__ == "__main__":
    main()