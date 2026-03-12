"""Interactive CLI demo: Auth0 Token Vault + Microsoft Agent Framework.

Run with:  python -m src.main
"""

import asyncio
import os

from dotenv import load_dotenv
from agent_framework import AgentSession

from auth0_ai_ms_agent.token_vault import TokenVaultInterrupt

from src.agent import create_agent
from src.connected_accounts import connect_account


def _handle_interrupt(interrupt: TokenVaultInterrupt, session: AgentSession) -> None:
    """Handle a TokenVaultInterrupt by running the Connected Accounts flow."""
    connection = interrupt.connection
    scopes = getattr(interrupt, "scopes", [])

    print(f"\n\U0001f510  Token Vault authorization required for '{connection}'!")
    if scopes:
        print(f"   Scopes: {scopes}")
    print()

    success = connect_account(connection, scopes)

    if success:
        print("   Try your request again.\n")
    else:
        print("\n   \u274c  Connection was not completed.")
        print("   Check Auth0 Dashboard settings and try again.\n")

    session.state.pop("pending_interrupt", None)


async def main() -> None:
    load_dotenv()

    required = ["AUTH0_DOMAIN", "AUTH0_CLIENT_ID", "AUTH0_CLIENT_SECRET",
                 "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"]
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        print(f"\n\u274c  Missing environment variables: {', '.join(missing)}")
        print("   Copy .env.example \u2192 .env and fill in the values.\n")
        return

    if not os.environ.get("USER_REFRESH_TOKEN"):
        print("\n\u26a0\ufe0f   Not logged in. Run first:\n")
        print("     python -m src.login\n")
        return

    agent = create_agent()
    session = AgentSession()

    print("=" * 60)
    print("  Auth0 Token Vault + Microsoft Agent Framework Demo")
    print("=" * 60)
    print()
    print("Try prompts like:")
    print('  \u2022 "List my GitHub repos"')
    print('  \u2022 "Am I free on Friday at 10am?"')
    print()
    print("Type 'quit' or 'exit' to stop.\n")

    while True:
        try:
            user_input = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            print("Goodbye!")
            break

        try:
            result = await agent.run(
                user_input,
                session=session,
                options={"additional_function_arguments": {"session": session}},
            )

            interrupt = session.state.get("pending_interrupt")
            if isinstance(interrupt, TokenVaultInterrupt):
                _handle_interrupt(interrupt, session)
            else:
                print(f"\nAgent> {result}\n")

        except TokenVaultInterrupt as exc:
            _handle_interrupt(exc, session)

        except Exception as exc:
            print(f"\n\u26a0\ufe0f  Error: {exc}\n")


def run():
    asyncio.run(main())


if __name__ == "__main__":
    run()
