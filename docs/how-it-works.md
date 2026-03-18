# How It Works

## Overview

The Okta/Auth0 team built an integration between **Auth0 Token Vault** and the Microsoft Agent Framework (MAF):

* https://github.com/auth0/auth0-ai-python/tree/main/packages/auth0-ai-ms-agent

**Key idea:**
Auth0 Token Vault manages **refresh tokens + access tokens on behalf of an AI agent**, tied to a user's Auth0 identity. The agent never handles raw provider credentials — Token Vault exchanges them transparently.

---

## What This Demo Does

This sample agent combines Microsoft Foundry + Auth0:

* https://github.com/michaelsrichter/auth0-token-vault-agent-demo

The agent:

* Authenticates the user via Auth0
* Uses Token Vault to securely access the **GitHub API** (repo listings)

> **⚠️ Note:** A **Google Calendar** tool is also present in the source code, but it has **not been tested** and is **not guaranteed to work**.

---

## Step-by-Step Flow

### 1) User logs in via Auth0

* Run `python -m src.login`
* Your browser opens to the Auth0 login page
* Auth0 lets you choose a login provider (Google, GitHub, etc.)
* In this demo, **GitHub login is enabled**

> **Important:**
> You are logging into **Auth0**, not GitHub directly.
> GitHub is just the **identity provider** here.
> The refresh token you receive back is an **Auth0 refresh token** — not a GitHub token.

Code reference: [`src/login.py` → `login()`](../src/login.py#L121)

---

### 2) Agent runs (authenticated to Auth0)

The agent is configured with two tools — one for GitHub (tested and verified) and one for Google Calendar (**untested — not guaranteed to work**):

Code reference: [`src/agent.py`](../src/agent.py)

---

### 3) First GitHub API call triggers authorization

When the agent tries to call GitHub:

* It **does not yet have a GitHub access token** stored in Token Vault
* It raises a `TokenVaultInterrupt`, which the CLI handles by prompting:
  *"🔐 Token Vault authorization required for 'github'!"*
* A browser window opens for the user to authorize the GitHub connection

Code reference: [`src/main.py` → `_handle_interrupt()`](../src/main.py#L18)

---

### 4) Token Vault stores GitHub credentials

After the user grants consent in the browser:

* The Connected Accounts flow completes via the Auth0 My Account API
* Auth0 Token Vault stores the GitHub refresh token
* Future access tokens are managed and refreshed automatically

Code reference: [`src/connected_accounts.py`](../src/connected_accounts.py)

---

### 5) Subsequent calls just work

Now when the agent calls the GitHub tool:

* Token Vault returns a fresh GitHub access token
* The tool calls the GitHub API successfully
* No user interaction is needed

Code reference: [`src/tools/github_tool.py`](../src/tools/github_tool.py)

---

## Workflow Diagram

```
[User]
   │
   │ 1. python -m src.login
   ▼
[Auth0 Login Page]
   │
   │ (via GitHub / Google / etc.)
   ▼
[Auth0 Identity Created]
   │
   │ Auth0 Refresh Token saved to .env
   ▼
[Agent Runs (python -m src.main)]
   │
   │ 3. User asks: "List my GitHub repos"
   ▼
[GitHub Tool Called]
   │
   │ No GitHub token in Token Vault yet →
   │ TokenVaultInterrupt raised
   ▼
[Connected Accounts Flow]
   │
   │ Browser opens → User authorizes GitHub
   ▼
[Auth0 Token Vault]
   │
   │ Stores GitHub refresh token
   │ Returns access tokens on demand
   ▼
[GitHub API]
   │
   ▼
[Agent Returns Repo List]
```

---

## Setup Notes

Only **one GitHub App** is required. It is used for two purposes:

1. **Logging into Auth0** (social / identity login)
2. **Token Vault** — accessing GitHub APIs on the user's behalf

Auth0 configuration steps:
[README → Configure the GitHub Connection in Auth0](../README.md#5-configure-the-github-connection-in-auth0)

---

## Key Takeaways

* **Auth0** = identity provider + token broker
* **Token Vault** = secure token storage + automatic access token exchange
* The agent **never handles raw credentials** — only short-lived access tokens provided by Token Vault
* Works with multiple providers (GitHub, Google, and others); **note that only GitHub has been tested and verified**
* Clean separation of concerns:
  * **Who the user is** → Auth0 identity
  * **What APIs the agent can access** → Token Vault manages provider tokens

---

## Final Note

You can run this entire demo with a **free Auth0 account**.

This is a solid foundation for building a production-ready reference architecture for agentic apps that need to call external APIs on behalf of users.
