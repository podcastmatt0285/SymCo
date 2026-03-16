"""
Fetch all commits from GitHub and post them as patch notes to the Updates channel.

Run with:
    PYTHONPATH=venv/lib/python3.12/site-packages python3.12 post_patch_notes.py

Set GITHUB_TOKEN env var for private repos or to avoid rate limits:
    GITHUB_TOKEN=ghp_xxx python3.12 post_patch_notes.py

Re-running this script is safe — each commit is keyed by its SHA so existing
entries are updated in place rather than duplicated.
"""
import json
import os
import time
import urllib.error
import urllib.request

from admins import post_update

ADMIN_ID = 1
REPO = "podcastmatt0285/SymCo"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")


def _gh_headers() -> dict:
    h = {"Accept": "application/vnd.github.v3+json", "User-Agent": "wadsworth-patch-notes"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"token {GITHUB_TOKEN}"
    return h


def fetch_all_commits() -> list:
    """Fetch every commit from GitHub, following pagination links."""
    commits = []
    url = f"https://api.github.com/repos/{REPO}/commits?per_page=100"
    while url:
        req = urllib.request.Request(url, headers=_gh_headers())
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                commits.extend(json.loads(resp.read().decode()))
                link = resp.headers.get("Link", "")
                url = None
                for part in link.split(","):
                    part = part.strip()
                    if 'rel="next"' in part:
                        url = part.split(";")[0].strip().strip("<>")
                        break
        except urllib.error.HTTPError as e:
            print(f"GitHub API error: {e.code} {e.reason}")
            break
        except Exception as e:
            print(f"Error fetching commits: {e}")
            break
    return commits


def commit_to_note(commit: dict) -> str:
    """Convert a GitHub commit object to a patch-note string (≤500 chars)."""
    raw = commit.get("commit", {}).get("message", "").strip()
    # Use only the subject + first body paragraph (split on blank line)
    parts = raw.split("\n\n")
    text = parts[0].strip()
    # Drop any trailing session URL lines
    lines = [l for l in text.splitlines()
             if not l.strip().startswith("https://claude.ai/code/session_")]
    text = "\n".join(lines).strip()
    if len(text) > 500:
        text = text[:497] + "..."
    return text


def main():
    print(f"Fetching commits from github.com/{REPO} ...")
    commits = fetch_all_commits()
    if not commits:
        print("No commits found. Set GITHUB_TOKEN if the repo is private.")
        return

    # Reverse so we post oldest → newest (chronological order in the channel)
    commits = list(reversed(commits))
    print(f"Found {len(commits)} commits. Upserting to Updates channel...\n")

    ok_count = 0
    for i, commit in enumerate(commits, 1):
        sha = commit.get("sha", "")[:7]
        content = commit_to_note(commit)
        if not content:
            print(f"  [{i:03d}] {sha} — empty message, skipping")
            continue
        tag = f"commit_{sha}"
        result = post_update(ADMIN_ID, content, tag=tag)
        if result.get("ok"):
            ok_count += 1
            status = "OK"
        else:
            status = f"FAILED: {result.get('error')}"
        title = content.splitlines()[0][:50]
        print(f"  [{i:03d}] {sha}  {title:<50}  {status}")
        time.sleep(0.05)

    print(f"\nDone — {ok_count}/{len(commits)} posted. Re-running will update in place.")


if __name__ == "__main__":
    main()
