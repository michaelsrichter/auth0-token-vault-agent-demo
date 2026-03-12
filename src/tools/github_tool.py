"""GitHub tool secured with Auth0 Token Vault."""

import httpx
from agent_framework import FunctionTool

from auth0_ai_ms_agent.auth0_ai import Auth0AI
from auth0_ai_ms_agent.token_vault import get_access_token_from_token_vault

from src.session import get_refresh_token


def build_github_tool(auth0_ai: Auth0AI) -> FunctionTool:
    with_github_access = auth0_ai.with_token_vault(
        connection="github",
        scopes=["openid", "read:user", "repo"],
        refresh_token=get_refresh_token,
    )

    def list_my_repos() -> str:
        """List the authenticated user's GitHub repositories."""
        token = get_access_token_from_token_vault()
        resp = httpx.get(
            "https://api.github.com/user/repos",
            headers={"Authorization": f"Bearer {token}",
                     "Accept": "application/vnd.github+json"},
            params={"sort": "updated", "per_page": 10},
            timeout=15,
        )
        resp.raise_for_status()
        repos = resp.json()
        if not repos:
            return "You have no GitHub repositories."
        lines = [f"- **{r['full_name']}** \u2014 {r.get('description') or '(no description)'}"
                 for r in repos]
        return "Your 10 most recently updated repos:\n" + "\n".join(lines)

    return with_github_access(FunctionTool(
        name="list_my_github_repos",
        description="Lists the user's GitHub repositories (10 most recently updated).",
        func=list_my_repos,
    ))
