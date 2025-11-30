# Blame Router

Two CLI tools that reduce the social friction of asking questions about code.

## The Problem

The pain isn't finding "Dave." The pain is that Dave is busy, the code is old, and you—the new engineer—don't know what to ask. These tools automate the **transaction cost of context**.

## Tools

### `ask.py` - The Blame Router

Point at a confusing line of code. Get a smart question auto-generated and routed to the author.

```bash
python ask.py <file_path> <line_number>
```

**Example:**
```bash
python ask.py src/billing.py 42
```

**Output:**
```
📧 Author: dave@company.com
💬 Commit: "tax rate update"

✨ Magic Question:
"Hey, I'm reviewing `billing.py`. I see a 5% tax rate hardcoded on line 42.
Is this derived from the 2023 CA Regulatory update, or is it a placeholder?"

📨 SLACK MESSAGE (simulated)
TO: dave@company.com
```

### `crisk.py` - Change Risk Checker

Before you push, find files semantically related to your changes and identify their owners.

```bash
python crisk.py check [--draft]
```

**Example:**
```bash
git add src/client.py
python crisk.py check --draft
```

**Output:**
```
⚠️  Your changes may impact:

1. __init__.py (relevance: 0.82)
   → Owner: jonathan@company.com

2. auth.py (relevance: 0.78)
   → Owner: jonathan@company.com

DRAFT MESSAGE:
"Hey, I'm updating client.py to support new API key formats.
This might impact auth.py and __init__.py. Any concerns?"

📬 Recipients:
   • jonathan@company.com (8 files)
```

## Quick Start (Cloud Version)

### Install

```bash
pip install git+https://github.com/rohankatakam/fasho.ski.git
```

Or with uv:
```bash
uv pip install git+https://github.com/rohankatakam/fasho.ski.git
```

### Login

```bash
crisk login
```

This opens your browser to authenticate with [coderisk.dev](https://coderisk.dev). Once logged in, you're ready to go.

### Use

```bash
git add src/client.py
crisk check --draft
```

---

## Local Setup (Self-hosted)

If you want to run everything locally with your own API keys:

### 1. Install dependencies

```bash
pip install google-genai python-dotenv requests
```

### 2. Create `.env` file

```bash
cp .env.example .env
```

Add your API keys:
```
GEMINI_API_KEY=your_gemini_api_key
RELACE_API_KEY=your_relace_api_key
```

### 3. Run from a git repository

Both tools require being run from within a git repository.

## How It Works

### ask.py
1. **Archaeologist**: Runs `git blame` to find who wrote the line and their commit message
2. **Investigator**: Sends context to Gemini to generate a hypothesis-driven question
3. **Router**: Outputs the message (Slack integration simulated)

### crisk.py
1. Gets your staged diff (`git diff --cached`)
2. Sends codebase to Relace semantic search API
3. Finds files semantically related to your changes
4. Runs `git blame` to identify owners of related files
5. Uses Gemini to draft a notification message

## The Pitch

> "Everyone else is building tools to *search* code. I built a tool that *talks* to the people who wrote it. It turns a 30-minute 'Zoom?' interruption into a 30-second Slack reply."

## License

MIT
