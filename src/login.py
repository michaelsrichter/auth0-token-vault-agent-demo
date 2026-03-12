"""Auth0 login flow — opens browser, catches callback, saves refresh token.

Run with:  python -m src.login
"""

import http.server
import os
import secrets
import socket
import sys
import threading
import urllib.parse
import webbrowser

import httpx
from dotenv import load_dotenv, set_key

CALLBACK_PORT = 3000
CALLBACK_PATH = "/auth/callback"
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}{CALLBACK_PATH}"


def _get_env_path() -> str:
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if not os.path.exists(env_path):
        env_path = os.path.join(os.getcwd(), ".env")
    return env_path


def save_refresh_token(refresh_token: str) -> None:
    """Save the refresh token to .env and update the current process env."""
    set_key(_get_env_path(), "USER_REFRESH_TOKEN", refresh_token)
    os.environ["USER_REFRESH_TOKEN"] = refresh_token


def run_callback_server() -> dict | None:
    """Start localhost:3000, wait for one GET to /auth/callback.

    Exchanges the authorization code for tokens automatically.
    Returns the full token response dict, or an error dict.
    """
    result: dict | None = None
    stop = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            nonlocal result
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != CALLBACK_PATH:
                self.send_response(404)
                self.end_headers()
                return

            params = urllib.parse.parse_qs(parsed.query)

            if "error" in params:
                result = {"error": params["error"][0],
                          "description": params.get("error_description", [""])[0]}
                self._html("Authorization failed. You can close this tab.")
                stop.set()
                return

            # Accept either 'code' (login) or 'connect_code' (connected accounts)
            code = (params.get("code") or params.get("connect_code") or [None])[0]
            if not code:
                result = {"error": "no_code", "params": {k: v[0] for k, v in params.items()}}
                self._html("No code received. You can close this tab.")
                stop.set()
                return

            # If this is a connect_code (from Connected Accounts flow), don't exchange
            if "connect_code" in params:
                result = {"connect_code": code}
                self._html("\u2705 Connected! You can close this tab.")
                stop.set()
                return

            # Exchange authorization code for tokens
            resp = httpx.post(
                f"https://{os.environ['AUTH0_DOMAIN']}/oauth/token",
                json={
                    "grant_type": "authorization_code",
                    "client_id": os.environ["AUTH0_CLIENT_ID"],
                    "client_secret": os.environ["AUTH0_CLIENT_SECRET"],
                    "code": code,
                    "redirect_uri": REDIRECT_URI,
                },
                timeout=15,
            )
            if resp.status_code != 200:
                result = {"error": "token_exchange_failed", "description": resp.text}
                self._html("Token exchange failed.")
            else:
                result = resp.json()
                self._html("\u2705 Login successful! You can close this tab.")
            stop.set()

        def _html(self, msg: str):
            body = (
                '<!DOCTYPE html><html><body style="font-family:system-ui;'
                'display:flex;justify-content:center;align-items:center;height:100vh">'
                f'<h2>{msg}</h2></body></html>'
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body.encode())

    srv = http.server.HTTPServer(("127.0.0.1", CALLBACK_PORT), Handler)
    srv.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.timeout = 1
    while not stop.is_set():
        srv.handle_request()
    srv.server_close()
    return result


def login():
    """Run the interactive Auth0 login flow."""
    load_dotenv()

    for v in ("AUTH0_DOMAIN", "AUTH0_CLIENT_ID", "AUTH0_CLIENT_SECRET"):
        if not os.environ.get(v):
            print(f"\u274c  {v} is not set. Fill in .env first.")
            sys.exit(1)

    authorize_url = (
        f"https://{os.environ['AUTH0_DOMAIN']}/authorize?"
        + urllib.parse.urlencode({
            "response_type": "code",
            "client_id": os.environ["AUTH0_CLIENT_ID"],
            "redirect_uri": REDIRECT_URI,
            "scope": "openid profile email offline_access",
            "state": secrets.token_urlsafe(32),
            "prompt": "login",
        })
    )

    print("=" * 60)
    print("  Auth0 Login")
    print("=" * 60)
    print(f"\nOpening browser...\n  {authorize_url}\n")
    webbrowser.open(authorize_url)

    result = run_callback_server()

    if not result or "error" in result:
        print(f"\u274c  Login failed: {(result or {}).get('error', 'unknown')}")
        print(f"   {(result or {}).get('description', '')}")
        sys.exit(1)

    refresh_token = result.get("refresh_token")
    if not refresh_token:
        print("\u274c  No refresh token. Enable 'Refresh Token' grant and 'offline_access' scope.")
        sys.exit(1)

    save_refresh_token(refresh_token)
    print("\u2705  Login successful! Refresh token saved to .env")
    print("   Run the agent:  python -m src.main")


if __name__ == "__main__":
    login()
