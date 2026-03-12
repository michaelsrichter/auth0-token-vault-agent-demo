"""Session helper — provides the Auth0 refresh token to the SDK."""

import os


def get_refresh_token(*_args, **_kwargs) -> str:
    """Return the user's Auth0 refresh token from the environment."""
    token = os.environ.get("USER_REFRESH_TOKEN", "")
    if not token:
        raise RuntimeError("Not logged in. Run:  python -m src.login")
    return token
