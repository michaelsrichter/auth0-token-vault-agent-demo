"""Agent setup — wires Microsoft Agent Framework with Auth0 Token Vault tools."""

import os
from datetime import datetime

from auth0_ai_ms_agent.auth0_ai import Auth0AI
from agent_framework import Agent
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import DefaultAzureCredential

from src.tools.github_tool import build_github_tool
from src.tools.google_calendar_tool import build_google_calendar_tool

SYSTEM_PROMPT = """\
You are a helpful personal assistant with access to the user's GitHub account
and Google Calendar.

Always call the appropriate tool when the user asks about their repos or
calendar. Never refuse to call a tool or ask the user to authorize first —
the tools handle authorization automatically.

Current date/time: {now}
"""


def create_agent() -> Agent:
    auth0_ai = Auth0AI()

    github_tool = build_github_tool(auth0_ai)
    calendar_tool = build_google_calendar_tool(auth0_ai)

    client = AzureOpenAIChatClient(
        credential=DefaultAzureCredential(),
    )

    return Agent(
        client=client,
        name="Auth0VaultAgent",
        instructions=SYSTEM_PROMPT.format(now=datetime.now().isoformat()),
        tools=[github_tool, calendar_tool],
    )
