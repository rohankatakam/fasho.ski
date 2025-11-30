"""
Change Risk Check module.
Analyzes staged changes and identifies impacted files/owners via backend API.
"""

import subprocess
import sys
import os
import json
import requests
from typing import Optional

from .auth import load_token, is_authenticated, BACKEND_URL
from .logger import (
    log_separator, log_request, log_response, log_cache,
    log_error, log_info, log_debug
)


def get_staged_diff() -> str:
    """Get the staged git diff."""
    result = subprocess.run(
        ["git", "diff", "--cached"],
        capture_output=True, text=True
    )
    return result.stdout


def get_staged_files() -> list[str]:
    """Get list of staged file paths."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True, text=True
    )
    return [f for f in result.stdout.strip().split('\n') if f]


def get_git_remote() -> Optional[str]:
    """Get the git remote URL for the current repo."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_git_hash() -> Optional[str]:
    """Get the current git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_codebase_files() -> list[dict]:
    """Get all tracked files in the repo with their content."""
    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True, text=True
    )
    files = result.stdout.strip().split('\n')

    codebase = []
    for filepath in files:
        if not filepath:
            continue
        # Skip binary files and large files
        if any(filepath.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.zip', '.tar', '.gz', '.lock']):
            continue
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                # Skip very large files
                if len(content) > 50000:
                    continue
                codebase.append({
                    "filename": filepath,
                    "content": content
                })
        except (IOError, OSError):
            continue

    return codebase


def get_file_owner(filepath: str) -> str:
    """Get the primary author of a file using git blame."""
    try:
        result = subprocess.run(
            ["git", "blame", "--porcelain", filepath],
            capture_output=True, text=True
        )

        if result.returncode != 0:
            return "unknown"

        # Count commits by author
        authors = {}
        for line in result.stdout.split('\n'):
            if line.startswith("author-mail"):
                email = line.split("<")[1].rstrip(">") if "<" in line else "unknown"
                authors[email] = authors.get(email, 0) + 1

        if not authors:
            return "unknown"

        # Return most frequent author
        return max(authors, key=authors.get)
    except Exception:
        return "unknown"


def analyze_via_backend(
    diff: str,
    codebase: list[dict],
    staged_files: list[str],
    git_remote: Optional[str] = None,
    git_hash: Optional[str] = None
) -> Optional[dict]:
    """Call backend API to analyze changes."""
    token = load_token()

    if not token:
        log_error("No token found")
        print("❌ Not authenticated. Run 'crisk login' first.")
        return None

    log_info(f"Token loaded: {token[:20]}...")
    log_info(f"Backend URL: {BACKEND_URL}")

    headers = {
        "Authorization": f"Bearer {token}",
        "authorization": f"Bearer {token}",  # lowercase backup
        "x-auth-token": token,  # additional backup header
        "Content-Type": "application/json"
    }

    payload = {
        "diff": diff,
        "codebase": codebase,
        "staged_files": staged_files
    }

    # Include git info for caching if available
    if git_remote:
        payload["git_remote"] = git_remote
        log_info(f"Git remote: {git_remote}")
    if git_hash:
        payload["git_hash"] = git_hash
        log_debug(f"Git hash: {git_hash}")

    payload_json = json.dumps(payload)
    payload_size = len(payload_json)

    url = f"{BACKEND_URL}/api/analyze"
    log_request("POST", url, headers, payload_size)

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=120  # Increased timeout for first-time repo indexing
        )

        log_response(response.status_code, response.text[:1000] if response.text else None)

        if response.status_code == 401:
            log_error(f"Authentication failed: {response.text}")
            print("❌ Authentication expired. Run 'crisk login' again.")
            print(f"   Debug: Check ~/.crisk/crisk.log for details")
            return None

        if response.status_code != 200:
            log_error(f"Backend error {response.status_code}: {response.text}")
            print(f"❌ Backend error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   {error_data.get('error', response.text)}")
            except:
                print(f"   {response.text}")
            return None

        return response.json()

    except requests.exceptions.ConnectionError as e:
        log_error(f"Connection error to {BACKEND_URL}", e)
        print(f"❌ Cannot connect to backend at {BACKEND_URL}")
        print("   Make sure the backend server is running.")
        return None
    except requests.exceptions.Timeout as e:
        log_error("Request timeout", e)
        print("❌ Request timed out. The codebase might be too large.")
        return None
    except Exception as e:
        log_error(f"Unexpected error: {e}", e)
        print(f"❌ Error: {e}")
        return None


def run_check(auto_draft: bool = False) -> int:
    """
    Main check command:
    1. Get staged changes
    2. Load codebase
    3. Call backend API for analysis
    4. Display results
    """
    log_separator()
    log_info("Starting crisk check")

    print("\n🔍 CRISK CHECK - Change Risk Analysis")
    print("=" * 50)

    # Check authentication
    if not is_authenticated():
        log_error("Not authenticated")
        print("\n❌ Not authenticated. Run 'crisk login' first.")
        return 1

    # Step 1: Get staged diff
    print("\n📝 Getting staged changes...")
    diff = get_staged_diff()
    staged_files = get_staged_files()

    if not diff or not staged_files:
        log_info("No staged changes found")
        print("❌ No staged changes found. Run 'git add' first.")
        return 1

    log_info(f"Found {len(staged_files)} staged file(s): {staged_files}")
    print(f"   Found {len(staged_files)} staged file(s):")
    for f in staged_files:
        print(f"   • {f}")

    # Step 2: Get git info for caching
    git_remote = get_git_remote()
    git_hash = get_git_hash()

    if git_remote:
        print(f"\n🔗 Repository: {git_remote}")

    # Step 3: Get codebase
    print("\n📂 Loading codebase...")
    codebase = get_codebase_files()
    log_info(f"Indexed {len(codebase)} files")
    print(f"   Indexed {len(codebase)} files")

    # Step 4: Call backend
    print("\n🧠 Analyzing semantic relationships...")
    result = analyze_via_backend(diff, codebase, staged_files, git_remote, git_hash)

    if not result:
        return 1

    related_files = result.get("related_files", [])
    draft_message = result.get("draft_message", "")

    log_info(f"Found {len(related_files)} related files")

    if not related_files:
        print("\n✅ No significantly related files found.")
        print("   Your changes appear to be isolated.")
        return 0

    # Step 5: Get owners for each related file (done locally for speed)
    print("\n👥 Identifying code owners...")
    for r in related_files:
        r["owner"] = get_file_owner(r["filename"])

    # Step 6: Display results
    print("\n" + "=" * 50)
    print("⚠️  Your changes may impact:\n")

    for i, r in enumerate(related_files, 1):
        score = r.get("score", r.get("relevance", 0))
        print(f"{i}. {r['filename']} (relevance: {score:.2f})")
        print(f"   → Owner: {r['owner']}")
        print()

    # Step 7: Show draft message
    print("=" * 50)

    if auto_draft and draft_message:
        print("\n✍️  Generated draft message...")
        print("\n" + "-" * 50)
        print("DRAFT MESSAGE:")
        print("-" * 50)
        print(draft_message)
        print("-" * 50)

        # Group by owner
        owners = {}
        for r in related_files:
            owner = r["owner"]
            if owner not in owners:
                owners[owner] = []
            owners[owner].append(r["filename"])

        print("\n📬 Recipients:")
        for owner, files in owners.items():
            print(f"   • {owner}")
            for f in files:
                print(f"     - {f}")
    elif not auto_draft:
        try:
            response = input("\n📨 Generate draft message to owners? [y/n]: ").strip().lower()
            if response == 'y' and draft_message:
                print("\n" + "-" * 50)
                print("DRAFT MESSAGE:")
                print("-" * 50)
                print(draft_message)
                print("-" * 50)

                owners = {}
                for r in related_files:
                    owner = r["owner"]
                    if owner not in owners:
                        owners[owner] = []
                    owners[owner].append(r["filename"])

                print("\n📬 Recipients:")
                for owner, files in owners.items():
                    print(f"   • {owner}")
                    for f in files:
                        print(f"     - {f}")
        except EOFError:
            pass

    log_info("crisk check completed successfully")
    return 0
