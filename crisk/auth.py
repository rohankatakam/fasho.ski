"""
Authentication module for CRISK CLI.
Handles Clerk OAuth flow and token storage.
"""

import os
import json
import time
import webbrowser
import http.server
import socketserver
import urllib.parse
from pathlib import Path
from typing import Optional

# Config directory
CRISK_DIR = Path.home() / ".crisk"
TOKEN_FILE = CRISK_DIR / "token"
CONFIG_FILE = CRISK_DIR / "config.json"

# Backend URL - change this for production
BACKEND_URL = os.getenv("CRISK_BACKEND_URL", "http://localhost:3000")


def get_config_dir() -> Path:
    """Ensure config directory exists and return path."""
    CRISK_DIR.mkdir(exist_ok=True)
    return CRISK_DIR


def save_token(token: str) -> None:
    """Save authentication token to disk."""
    get_config_dir()
    TOKEN_FILE.write_text(token)
    # Secure permissions
    TOKEN_FILE.chmod(0o600)


def load_token() -> Optional[str]:
    """Load authentication token from disk."""
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()
    return None


def delete_token() -> None:
    """Delete stored authentication token."""
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()


def is_authenticated() -> bool:
    """Check if user has a valid token stored."""
    token = load_token()
    return token is not None and len(token) > 0


class AuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler to receive OAuth callback."""

    token = None
    error = None

    def do_GET(self):
        """Handle GET request from OAuth redirect."""
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "token" in params:
            AuthCallbackHandler.token = params["token"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>CRISK - Authenticated</title>
                <style>
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    }
                    .container {
                        text-align: center;
                        padding: 40px;
                        background: white;
                        border-radius: 12px;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
                    }
                    h1 { color: #22c55e; margin-bottom: 10px; }
                    p { color: #666; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>&#10003; Authentication Successful!</h1>
                    <p>You can close this window and return to your terminal.</p>
                </div>
            </body>
            </html>
            """)
        elif "error" in params:
            AuthCallbackHandler.error = params.get("error_description", params["error"])[0]
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>CRISK - Error</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        background: #f3f4f6;
                    }}
                    .container {{
                        text-align: center;
                        padding: 40px;
                        background: white;
                        border-radius: 12px;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                    }}
                    h1 {{ color: #ef4444; margin-bottom: 10px; }}
                    p {{ color: #666; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>&#10007; Authentication Failed</h1>
                    <p>{AuthCallbackHandler.error}</p>
                    <p>Please try again.</p>
                </div>
            </body>
            </html>
            """.encode())
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, format, *args):
        """Suppress logging."""
        pass


def login() -> bool:
    """
    Initiate login flow:
    1. Start local server to receive callback
    2. Open browser to Clerk auth page
    3. Wait for callback with token
    4. Save token to disk
    """
    print("\n🔐 CRISK Login")
    print("=" * 40)

    # Find available port
    port = 9876

    # Start local server
    server = socketserver.TCPServer(("", port), AuthCallbackHandler)
    server.timeout = 120  # 2 minute timeout

    # Build auth URL
    callback_url = f"http://localhost:{port}/callback"
    auth_url = f"{BACKEND_URL}/api/cli-auth?callback={urllib.parse.quote(callback_url)}"

    print(f"\n📱 Opening browser for authentication...")
    print(f"   If browser doesn't open, visit:")
    print(f"   {auth_url}\n")

    # Open browser
    webbrowser.open(auth_url)

    print("⏳ Waiting for authentication...")

    # Wait for callback
    AuthCallbackHandler.token = None
    AuthCallbackHandler.error = None

    start_time = time.time()
    while AuthCallbackHandler.token is None and AuthCallbackHandler.error is None:
        server.handle_request()
        if time.time() - start_time > 120:
            print("\n❌ Authentication timed out. Please try again.")
            server.server_close()
            return False

    server.server_close()

    if AuthCallbackHandler.error:
        print(f"\n❌ Authentication failed: {AuthCallbackHandler.error}")
        return False

    if AuthCallbackHandler.token:
        save_token(AuthCallbackHandler.token)
        print("\n✅ Successfully authenticated!")
        print("   Token saved to ~/.crisk/token")
        return True

    return False


def logout() -> None:
    """Log out by deleting stored token."""
    delete_token()
    print("\n✅ Logged out successfully.")
    print("   Token removed from ~/.crisk/token")
