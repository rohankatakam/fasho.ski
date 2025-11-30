#!/usr/bin/env python3
"""
The Blame Router
Run: python ask.py <file_path> <line_number>
Example: python ask.py jean-memory/sdk/python/jeanmemory/client.py 42
"""

import subprocess
import sys
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY not found in .env file")
    sys.exit(1)


def get_blame_info(file_path: str, line_number: int) -> dict:
    """
    Run git blame on a specific line and extract author info + context.
    Returns: {"author_email": "...", "code_snippet": "...", "commit_msg": "..."}
    """

    # Step 1: Run git blame on the specific line
    blame_cmd = [
        "git", "blame", "-L", f"{line_number},{line_number}",
        "--porcelain", file_path
    ]

    result = subprocess.run(blame_cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise Exception(f"git blame failed: {result.stderr}")

    # Parse porcelain output
    lines = result.stdout.strip().split('\n')
    commit_hash = lines[0].split()[0]

    author_email = None
    for line in lines:
        if line.startswith("author-mail"):
            # Format: author-mail <email@example.com>
            author_email = line.split("<")[1].rstrip(">")
            break

    # Step 2: Get the commit message
    show_cmd = ["git", "show", "-s", "--format=%s", commit_hash]
    result = subprocess.run(show_cmd, capture_output=True, text=True)
    commit_msg = result.stdout.strip()

    # Step 3: Read surrounding code (10 lines before and after)
    start_line = max(1, line_number - 10)
    end_line = line_number + 10

    with open(file_path, 'r') as f:
        all_lines = f.readlines()
        snippet_lines = all_lines[start_line-1:end_line]

        # Add line numbers for context
        code_snippet = ""
        for i, line in enumerate(snippet_lines, start=start_line):
            marker = ">>>" if i == line_number else "   "
            code_snippet += f"{marker} {i}: {line}"

    return {
        "author_email": author_email,
        "commit_hash": commit_hash,
        "commit_msg": commit_msg,
        "code_snippet": code_snippet,
        "file_path": file_path,
        "line_number": line_number
    }


def generate_magic_question(blame_info: dict) -> str:
    """
    Step 2: The Investigator
    Send blame info to Gemini and get a specific hypothesis question.
    """
    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""You are a Senior Engineer. A junior dev is confused by this code.

FILE: {blame_info['file_path']}
LINE: {blame_info['line_number']}
COMMIT MESSAGE: {blame_info['commit_msg']}

CODE CONTEXT:
{blame_info['code_snippet']}

Don't just ask 'What does this do?' Formulate a specific hypothesis based on the variable names and commit message. Ask a question that can be answered with a simple explanation. Be brief.

Write a short Slack message (2-3 sentences max) that:
1. References the specific file and line
2. States what you SEE (the confusing thing)
3. Proposes a hypothesis and asks if it's correct

Example: "Hey, I'm reviewing `billing.py`. I see a 5% tax rate hardcoded on line 42. Is this derived from the 2023 CA Regulatory update, or is it a placeholder?"
"""

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
    )

    return response.text


def send_slack_message(author_email: str, message: str):
    """
    Step 3: The Router (Mock Version)
    For now, just log what we WOULD send to Slack.
    """
    print(f"\n{'='*50}")
    print(f"📨 SLACK MESSAGE (simulated)")
    print(f"{'='*50}")
    print(f"TO: {author_email}")
    print(f"MESSAGE:\n{message}")
    print(f"{'='*50}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python ask.py <file_path> <line_number>")
        print("Example: python ask.py sdk/python/jeanmemory/client.py 42")
        sys.exit(1)

    file_path = sys.argv[1]
    line_number = int(sys.argv[2])

    # Step 1: The Archaeologist
    print(f"\n🔍 STEP 1: THE ARCHAEOLOGIST")
    print(f"{'='*50}")
    print(f"Investigating: {file_path}:{line_number}\n")

    info = get_blame_info(file_path, line_number)

    print(f"📧 Author: {info['author_email']}")
    print(f"🔗 Commit: {info['commit_hash'][:8]}")
    print(f"💬 Message: {info['commit_msg']}")
    print(f"\n📄 Code Context:")
    print("-" * 50)
    print(info['code_snippet'])
    print("-" * 50)

    # Step 2: The Investigator
    print(f"\n🧠 STEP 2: THE INVESTIGATOR")
    print(f"{'='*50}")
    print("Generating magic question with Gemini...")

    magic_question = generate_magic_question(info)

    print(f"\n✨ Magic Question:\n{magic_question}")

    # Step 3: The Router (simulated)
    print(f"\n📬 STEP 3: THE ROUTER")
    send_slack_message(info['author_email'], magic_question)
