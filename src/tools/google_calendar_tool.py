"""Google Calendar tool secured with Auth0 Token Vault.

WARNING: This tool has NOT been tested and is NOT guaranteed to work.
It is provided as a starting point only. Use at your own risk.
"""

import httpx
from datetime import datetime
from typing import Annotated
from pydantic import Field
from agent_framework import FunctionTool

from auth0_ai_ms_agent.auth0_ai import Auth0AI
from auth0_ai_ms_agent.token_vault import get_access_token_from_token_vault

from src.session import get_refresh_token


def build_google_calendar_tool(auth0_ai: Auth0AI) -> FunctionTool:
    with_google_calendar_access = auth0_ai.with_token_vault(
        connection="google-oauth2",
        scopes=["openid", "https://www.googleapis.com/auth/calendar.freebusy"],
        refresh_token=get_refresh_token,
    )

    def check_calendar(
        date: Annotated[str, Field(description="ISO 8601 date-time, e.g. '2026-03-15T10:00:00'")],
    ) -> str:
        """Check whether the user is free or busy at a given date/time."""
        token = get_access_token_from_token_vault()
        dt = datetime.fromisoformat(date)
        time_min = dt.isoformat() + "Z"
        time_max = dt.replace(hour=dt.hour + 1).isoformat() + "Z"

        resp = httpx.post(
            "https://www.googleapis.com/calendar/v3/freeBusy",
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
            json={"timeMin": time_min, "timeMax": time_max,
                  "items": [{"id": "primary"}]},
            timeout=15,
        )
        resp.raise_for_status()
        busy = resp.json().get("calendars", {}).get("primary", {}).get("busy", [])
        return f"You are {'BUSY' if busy else 'FREE'} on {date}."

    return with_google_calendar_access(FunctionTool(
        name="check_user_calendar",
        description="Check if the user is available (free or busy) at a specific date and time.",
        func=check_calendar,
    ))
