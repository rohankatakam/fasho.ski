#!/usr/bin/env python3
"""
CRISK CLI - Change Risk Analysis Tool

Commands:
    crisk login     - Authenticate with your coderisk.dev account
    crisk logout    - Log out and remove stored credentials
    crisk check     - Analyze staged changes for impacted files
    crisk status    - Show authentication status
"""

import sys
import os

# Allow overriding backend URL via environment
if "CRISK_BACKEND_URL" not in os.environ:
    os.environ["CRISK_BACKEND_URL"] = "https://coderisk.dev"


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "login":
        from .auth import login
        success = login()
        sys.exit(0 if success else 1)

    elif command == "logout":
        from .auth import logout
        logout()
        sys.exit(0)

    elif command == "check":
        from .check import run_check
        auto_draft = "--draft" in sys.argv
        exit_code = run_check(auto_draft=auto_draft)
        sys.exit(exit_code)

    elif command == "status":
        from .auth import is_authenticated, load_token, BACKEND_URL
        print("\n📊 CRISK Status")
        print("=" * 40)
        if is_authenticated():
            token = load_token()
            print(f"   ✅ Authenticated")
            print(f"   Token: {token[:20]}..." if token else "   Token: (none)")
        else:
            print("   ❌ Not authenticated")
            print("   Run 'crisk login' to authenticate")
        print(f"   Backend: {BACKEND_URL}")
        sys.exit(0)

    elif command in ["help", "-h", "--help"]:
        print_help()
        sys.exit(0)

    elif command == "version" or command == "-v" or command == "--version":
        from . import __version__
        print(f"crisk version {__version__}")
        sys.exit(0)

    else:
        print(f"Unknown command: {command}")
        print_help()
        sys.exit(1)


def print_help():
    """Print help message."""
    print("""
🔍 CRISK - Change Risk Analysis Tool

Usage: crisk <command> [options]

Commands:
    login           Authenticate with your coderisk.dev account
    logout          Log out and remove stored credentials
    check           Analyze staged changes for impacted files
    status          Show authentication status
    help            Show this help message
    version         Show version

Options for 'check':
    --draft         Automatically generate draft message

Examples:
    crisk login                 # Authenticate via browser
    crisk check                 # Analyze staged changes
    crisk check --draft         # Analyze and auto-generate message

Environment:
    CRISK_BACKEND_URL           Override backend URL (default: https://coderisk.dev)
""")


if __name__ == "__main__":
    main()
