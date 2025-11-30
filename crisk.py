#!/usr/bin/env python3
"""
crisk check - Change Risk Checker
Finds files semantically related to your staged changes and identifies their owners.

Usage: python crisk.py check
"""

import subprocess
import sys
import os
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

RELACE_API_KEY = os.getenv("RELACE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not RELACE_API_KEY or not GEMINI_API_KEY:
    print("Error: RELACE_API_KEY and GEMINI_API_KEY must be set in .env file")
    sys.exit(1)

RELACE_RANK_URL = "https://ranker.endpoint.relace.run/v2/code/rank"


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


def get_codebase_files() -> list[dict]:
    """Get all tracked files in the repo with their content."""
    # Get list of all tracked files
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
        if any(filepath.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.zip', '.tar', '.gz']):
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


def rank_related_files(diff: str, codebase: list[dict], staged_files: list[str]) -> list[dict]:
    """Use Relace API to find files semantically related to the diff."""

    # Build query from the diff
    query = f"""Find files that are semantically related to these code changes and might be impacted:

{diff}

What other files in this codebase might need to be updated, reviewed, or could be affected by these changes?"""

    headers = {
        "Authorization": f"Bearer {RELACE_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "query": query,
        "codebase": codebase,
        "token_limit": 100000
    }

    response = requests.post(RELACE_RANK_URL, json=payload, headers=headers)

    if response.status_code != 200:
        print(f"Error from Relace API: {response.status_code}")
        print(response.text)
        return []

    results = response.json().get("results", [])

    # Filter out the files that are already staged (we want OTHER related files)
    related = [r for r in results if r["filename"] not in staged_files]

    # Return top results with score > 0.3
    return [r for r in related[:10] if r["score"] > 0.3]


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


def generate_draft_message(staged_files: list[str], related_files: list[dict], diff: str) -> str:
    """Use Gemini to generate a draft message to send to owners."""

    client = genai.Client(api_key=GEMINI_API_KEY)

    related_summary = "\n".join([
        f"- {r['filename']} (owner: {r['owner']}, relevance: {r['score']:.2f})"
        for r in related_files
    ])

    prompt = f"""You are helping a developer notify code owners about potentially impacted files.

The developer is making changes to: {', '.join(staged_files)}

These files may be impacted:
{related_summary}

The actual diff:
```
{diff[:2000]}
```

Write a brief, friendly Slack message (3-4 sentences) that:
1. Mentions what files are being changed
2. Notes which files might be impacted
3. Asks if there are any concerns or dependencies to be aware of

Be concise and specific. Don't be overly formal."""

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
    )

    return response.text


def main():
    if len(sys.argv) < 2 or sys.argv[1] != "check":
        print("Usage: python crisk.py check [--draft]")
        print("\nRun this command after staging your changes (git add ...)")
        print("  --draft    Automatically generate draft message")
        sys.exit(1)

    auto_draft = "--draft" in sys.argv

    print("\n🔍 CRISK CHECK - Change Risk Analysis")
    print("=" * 50)

    # Step 1: Get staged diff
    print("\n📝 Getting staged changes...")
    diff = get_staged_diff()
    staged_files = get_staged_files()

    if not diff or not staged_files:
        print("❌ No staged changes found. Run 'git add' first.")
        sys.exit(1)

    print(f"   Found {len(staged_files)} staged file(s):")
    for f in staged_files:
        print(f"   • {f}")

    # Step 2: Get codebase
    print("\n📂 Loading codebase...")
    codebase = get_codebase_files()
    print(f"   Indexed {len(codebase)} files")

    # Step 3: Find related files via Relace
    print("\n🧠 Analyzing semantic relationships...")
    related = rank_related_files(diff, codebase, staged_files)

    if not related:
        print("\n✅ No significantly related files found.")
        print("   Your changes appear to be isolated.")
        sys.exit(0)

    # Step 4: Get owners for each related file
    print("\n👥 Identifying code owners...")
    for r in related:
        r["owner"] = get_file_owner(r["filename"])

    # Step 5: Display results
    print("\n" + "=" * 50)
    print("⚠️  Your changes may impact:\n")

    for i, r in enumerate(related, 1):
        print(f"{i}. {r['filename']} (relevance: {r['score']:.2f})")
        print(f"   → Owner: {r['owner']}")
        print()

    # Step 6: Offer to draft message
    print("=" * 50)

    if auto_draft:
        should_draft = True
    else:
        try:
            response = input("\n📨 Draft message to owners? [y/n]: ").strip().lower()
            should_draft = response == 'y'
        except EOFError:
            should_draft = False

    if should_draft:
        print("\n✍️  Generating draft message...")
        message = generate_draft_message(staged_files, related, diff)

        print("\n" + "-" * 50)
        print("DRAFT MESSAGE:")
        print("-" * 50)
        print(message)
        print("-" * 50)

        # Group by owner
        owners = {}
        for r in related:
            owner = r["owner"]
            if owner not in owners:
                owners[owner] = []
            owners[owner].append(r["filename"])

        print("\n📬 Recipients:")
        for owner, files in owners.items():
            print(f"   • {owner}")
            for f in files:
                print(f"     - {f}")


if __name__ == "__main__":
    main()
