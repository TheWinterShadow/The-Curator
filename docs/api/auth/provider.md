---
title: Google OAuth Provider
icon: material/shield-lock
---

# Google OAuth Provider

Implements `OAuthAuthorizationServerProvider` from the MCP SDK, delegating identity verification to Google while owning the full OAuth 2.1 state machine.

## Overview

The provider handles:

- **Dynamic Client Registration** — MCP clients register themselves on first connection.
- **Authorization** — Redirects clients to Google's authorization endpoint; stores pending auth state in GCS.
- **Google callback** — Exchanges the Google code for a userinfo token, verifies the email, and mints an MCP authorization code.
- **Token exchange** — Exchanges MCP authorization codes for access/refresh token pairs.
- **Token refresh** — Issues new access tokens from valid refresh tokens.
- **Token revocation** — Removes both the access token and all associated refresh tokens (or vice versa).

## State persistence

All OAuth state is stored in a single JSON blob at `oauth-state/state.json` in the GCS bucket configured by `OAUTH_STATE_BUCKET`. The blob is read at startup and written synchronously after every mutation. This ensures sessions survive Cloud Run container restarts and scale-to-zero events.

The blob contains:

```json
{
  "clients": { "<client_id>": { ... } },
  "auth_codes": { "<code>": { ... } },
  "access_tokens": { "<token>": { ... } },
  "refresh_tokens": { "<token>": { ... } },
  "pending_auths": { "<google_state>": { ... } }
}
```

Expired tokens are filtered out on load and never written back.

## Token lifetimes

| Token | TTL |
| --- | --- |
| Access token | 3,600 s (1 hour) |
| Refresh token | 2,592,000 s (30 days) |
| Authorization code | 300 s (5 minutes) |
| Pending auth state | 600 s (10 minutes) |

## Module reference

::: the_curator.auth.provider
