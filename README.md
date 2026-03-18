# Auth0 Token Vault + Microsoft Agent Framework Demo

An interactive CLI agent that calls the **GitHub** API on the user's behalf using [Auth0 Token Vault](https://auth0.com/docs/secure/call-apis-on-users-behalf/token-vault) and [Microsoft Agent Framework](https://github.com/microsoft/agent-framework).

> **⚠️ Note:** A **Google Calendar** tool is included in the source code but has **not been tested** and is **not guaranteed to work**. Only the GitHub tool has been verified end-to-end.

The LLM is hosted on **Azure OpenAI** (Microsoft Foundry) and authenticated via `DefaultAzureCredential` (`az login`).

```
User prompt → MS Agent Framework → Azure OpenAI (gpt-4o)
                      │
           Auth0 Token Vault  ← exchanges Auth0 refresh token
                      │           for provider access tokens
              ┌───────┼───────┐
              ▼       ▼       ▼
          GitHub  Calendar  (other APIs)
```

---

## Prerequisites

| Requirement | How to get it |
|---|---|
| **Python 3.11+** | `uv python install 3.11` or system package manager |
| **Azure CLI** | `az login` — provides Azure OpenAI credentials |
| **Azure OpenAI resource** | With a deployed chat model (e.g. `gpt-4o`) |
| **Auth0 account** | Free tier at [auth0.com/signup](https://auth0.com/signup) |

---

## Auth0 Setup (one-time)

### 1. Create an Auth0 Application

1. **Auth0 Dashboard → Applications → Create Application**
2. Type: **Regular Web Application**
3. Note the **Domain**, **Client ID**, and **Client Secret**
4. Under **Settings**:
   - **Allowed Callback URLs**: `http://localhost:3000/auth/callback`
   - **Allowed Logout URLs**: `http://localhost:3000`
5. Under **Settings → Advanced Settings → Grant Types**, enable:
   - `Authorization Code`
   - `Refresh Token`
   - `Token Vault`
6. **Disable Refresh Token Rotation** (required for Token Vault)

### 2. Enable Multi-Resource Refresh Token (MRRT)

1. In your app settings, scroll to **Multi-Resource Refresh Token**
2. Click **Edit Configuration**
3. Toggle ON the **My Account API**
4. Save

### 3. Activate the My Account API

1. **Auth0 Dashboard → Applications → APIs**
2. Find **Auth0 My Account API** → activate it
3. Click it → **Application Access** tab
4. Find your app → click **Edit**:
   - Set Authorization to **Authorized**
   - Enable scopes: `create:me:connected_accounts`, `read:me:connected_accounts`, `delete:me:connected_accounts`
5. Save
6. On the **Settings** tab → enable **Allow Skipping User Consent**

### 4. Create a GitHub App (not OAuth App)

Token Vault requires the upstream provider to issue refresh tokens. GitHub OAuth Apps don't support this — you need a **GitHub App**.

1. Go to **https://github.com/settings/apps** → **New GitHub App**
2. Fill in:
   - **App name**: anything (e.g. `Auth0 Token Vault`)
   - **Homepage URL**: `http://localhost:3000`
   - **Callback URL**: `https://YOUR_AUTH0_DOMAIN/login/callback`
   - **Webhook**: uncheck **Active** (not needed)
   - **Permissions**: `Contents: Read-only`, `Metadata: Read-only` (or whatever you need)
3. Click **Create GitHub App**
4. Generate a **Client Secret**
5. Copy the **Client ID** and **Client Secret**

### 5. Configure the GitHub Connection in Auth0

1. **Auth0 Dashboard → Authentication → Social → GitHub**
2. Enter the **Client ID** and **Client Secret** from the GitHub App
3. Under **Purpose**, select: **Authentication and Connected Accounts for Token Vault**
4. Under **Permissions**, check: `read:user`, `repo` (or whatever scopes you need)
5. Go to the **Applications** tab → toggle ON for your app
6. Save

### 6. (Optional) Google Calendar Connection

> **⚠️ Warning:** The Google Calendar integration is **not tested** and **not guaranteed to work**. The steps below and the corresponding source code (`src/tools/google_calendar_tool.py`) are provided as a starting point only. Use at your own risk.

1. **Auth0 Dashboard → Authentication → Social → Google**
2. Create a [Google OAuth 2.0 Client](https://console.cloud.google.com/apis/credentials)
3. Grant scope: `https://www.googleapis.com/auth/calendar.freebusy`
4. Under **Purpose**: **Authentication and Connected Accounts for Token Vault**
5. Enable **Offline Access**
6. Enable it for your app

---

## Installation

> **Note:** `auth0-ai` and `auth0-ai-ms-agent` are installed directly from the
> [auth0/auth0-ai-python](https://github.com/auth0/auth0-ai-python) GitHub repo
> (not PyPI) because the Token Vault support requires the latest unreleased source.
> See `pyproject.toml` for the git references.

```bash
# Create a Python 3.11+ virtual environment
uv venv --python 3.11 .venv
source .venv/bin/activate

# Install
pip install -e .

# Copy env template and fill in your values
cp .env.example .env
```

### Fill in `.env`

```env
# Auth0
AUTH0_DOMAIN=dev-XXXXXXXX.us.auth0.com
AUTH0_CLIENT_ID=your-client-id
AUTH0_CLIENT_SECRET=your-client-secret

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4o
```

Make sure you're logged into Azure:
```bash
az login
```

---

## Usage

### Step 1: Log in via Auth0

```bash
python -m src.login
```

Opens your browser to Auth0. Authenticate and the refresh token is saved to `.env` automatically.

### Step 2: Run the agent

```bash
python -m src.main
```

### Step 3: Try it

```
You> List my GitHub repos
```

**First time only**: If the GitHub connection isn't linked to Token Vault yet, the agent will automatically run the Connected Accounts flow — your browser opens, you authorize GitHub, and the tokens are stored in Token Vault. Then retry the same prompt.

After the first connection, Token Vault handles token exchange transparently.

> **⚠️ Note:** The agent also includes a Google Calendar tool (`check_user_calendar`), but it has **not been tested** and is **not guaranteed to work**.

---

## How It Works

> For a detailed walkthrough of the end-to-end flow, see **[docs/how-it-works.md](docs/how-it-works.md)**.

### Token Vault Flow

1. User logs in via Auth0 → gets an Auth0 refresh token
2. Agent tool calls Auth0's token exchange endpoint with the refresh token
3. Auth0 Token Vault returns a GitHub/Google access token
4. The tool uses the access token to call the external API

### Connected Accounts (first-time setup)

When Token Vault doesn't have stored tokens for a provider, it raises a `TokenVaultInterrupt`. The demo handles this by:

1. Getting a My Account API access token
2. Calling `/me/v1/connected-accounts/connect` to initiate linking
3. Opening the browser for the user to authorize
4. Calling `/me/v1/connected-accounts/complete` to finalize
5. Token Vault now stores the provider's tokens

This only needs to happen once per user per provider.

---

## Project Structure

```
auth01agent1/
├── .env.example              # Environment template
├── pyproject.toml             # Dependencies (installs from auth0-ai-python git)
├── README.md
└── src/
    ├── main.py                # CLI entry point + interrupt handler
    ├── agent.py               # Agent config (Azure OpenAI + Auth0 tools)
    ├── login.py               # Auth0 browser login flow
    ├── connected_accounts.py  # Connected Accounts flow (My Account API)
    ├── session.py             # Refresh token provider
    └── tools/
        ├── github_tool.py           # GitHub repos tool
        └── google_calendar_tool.py  # Google Calendar free/busy tool
```

---

## Configuration Reference

| What | Where | Notes |
|---|---|---|
| Auth0 Domain | `.env` → `AUTH0_DOMAIN` | e.g. `dev-xxx.us.auth0.com` |
| Auth0 Client ID | `.env` → `AUTH0_CLIENT_ID` | From Auth0 Dashboard |
| Auth0 Client Secret | `.env` → `AUTH0_CLIENT_SECRET` | From Auth0 Dashboard |
| Azure OpenAI Endpoint | `.env` → `AZURE_OPENAI_ENDPOINT` | e.g. `https://myresource.openai.azure.com/` |
| Azure OpenAI Deployment | `.env` → `AZURE_OPENAI_CHAT_DEPLOYMENT_NAME` | e.g. `gpt-4o` |
| Azure Auth | `az login` | No API key needed |
| User Token | `.env` → `USER_REFRESH_TOKEN` | Auto-saved by `python -m src.login` |
| GitHub connection name | `src/tools/github_tool.py` | Default: `"github"` |
| Google connection name | `src/tools/google_calendar_tool.py` | Default: `"google-oauth2"` (**untested — not guaranteed to work**) |

---

## License

Apache 2.0
