"""Connected Accounts flow for Auth0 Token Vault.

When the agent's tool triggers a TokenVaultInterrupt, this module runs the
My Account API Connected Accounts flow to link the external provider
(e.g. GitHub) so Token Vault can store and exchange its tokens.
"""

import os
import secrets
import webbrowser

import httpx

from src.login import CALLBACK_PORT, CALLBACK_PATH, REDIRECT_URI, run_callback_server, save_refresh_token


def connect_account(connection: str, scopes: list[str] | None = None) -> bool:
    """Run the Connected Accounts flow to link an external provider to Token Vault.

    Returns True on success, False on failure.
    """
    domain = os.environ["AUTH0_DOMAIN"]
    client_id = os.environ["AUTH0_CLIENT_ID"]
    client_secret = os.environ["AUTH0_CLIENT_SECRET"]
    refresh_token = os.environ.get("USER_REFRESH_TOKEN", "")

    if not refresh_token:
        print("   \u274c  No refresh token. Run: python -m src.login")
        return False

    # Step 1: Get a My Account API access token
    print("   Getting My Account API token...")
    resp = httpx.post(
        f"https://{domain}/oauth/token",
        json={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "audience": f"https://{domain}/me/",
            "scope": "openid profile offline_access "
                     "create:me:connected_accounts read:me:connected_accounts",
        },
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"   \u274c  Failed to get My Account API token: {resp.text}")
        return False

    token_data = resp.json()
    my_account_token = token_data["access_token"]

    # Update refresh token if rotated
    if new_rt := token_data.get("refresh_token"):
        save_refresh_token(new_rt)

    # Step 2: Initiate Connected Accounts
    print(f"   Initiating Connected Accounts for '{connection}'...")
    payload: dict = {
        "connection": connection,
        "redirect_uri": REDIRECT_URI,
        "state": secrets.token_urlsafe(32),
    }
    if scopes:
        payload["scopes"] = scopes

    resp2 = httpx.post(
        f"https://{domain}/me/v1/connected-accounts/connect",
        headers={"Authorization": f"Bearer {my_account_token}",
                 "Content-Type": "application/json"},
        json=payload,
        timeout=15,
    )
    if resp2.status_code not in (200, 201):
        print(f"   \u274c  Connect initiation failed: {resp2.text}")
        return False

    data = resp2.json()
    auth_session = data["auth_session"]
    ticket = data.get("connect_params", {}).get("ticket", "")
    connect_url = f"{data['connect_uri']}?ticket={ticket}"

    # Step 3: Open browser → user authorizes → callback with connect_code
    print("   Opening browser for authorization...")
    webbrowser.open(connect_url)
    result = run_callback_server()

    if not result:
        print("   \u274c  No response from authorization.")
        return False
    if "error" in result:
        print(f"   \u274c  Authorization failed: {result['error']}")
        print(f"      {result.get('description', '')}")
        return False

    connect_code = result.get("connect_code")
    if not connect_code:
        print("   \u274c  No connect_code received.")
        return False

    # Step 4: Complete the Connected Accounts flow
    print("   Completing Connected Accounts flow...")
    resp3 = httpx.post(
        f"https://{domain}/me/v1/connected-accounts/complete",
        headers={"Authorization": f"Bearer {my_account_token}",
                 "Content-Type": "application/json"},
        json={
            "auth_session": auth_session,
            "connect_code": connect_code,
            "redirect_uri": REDIRECT_URI,
        },
        timeout=15,
    )
    if resp3.status_code not in (200, 201, 204):
        print(f"   \u274c  Completion failed: {resp3.text}")
        return False

    print(f"   \u2705  '{connection}' connected to Token Vault!")
    return True
