---
title: Architecture
icon: material/layers-triple
---

# Architecture

## System diagram

```mermaid
flowchart TD
    Client["MCP Client\n(Claude Desktop, Cursor, Zed)"]
    CR["Cloud Run\nthe-curator"]
    Google["Google OAuth\naccounts.google.com"]
    Gemini["Vertex AI Gemini\nTranscript generation"]
    TTS["Vertex AI TTS\ngemini-3.1-flash-tts-preview"]
    GCS_EP["GCS Bucket\nthe-curator-podcast-data\n(episodes)"]
    GCS_AUTH["GCS Bucket\nthe-curator-oauth-state\n(tokens)"]
    SM["Secret Manager\nOAuth credentials"]

    Client -- "SSE /sse" --> CR
    Client -- "OAuth flow" --> Google
    Google -- "callback /oauth2/callback" --> CR
    CR -- "generate transcript" --> Gemini
    CR -- "synthesize audio" --> TTS
    CR -- "upload episode" --> GCS_EP
    CR -- "persist OAuth state" --> GCS_AUTH
    CR -- "read secrets at startup" --> SM
```

## Component breakdown

### FastMCP server ([`main.py`](../api/main.md))

The entry point. Wraps two MCP tools and wires together:

- The `GoogleOAuthProvider` as the MCP auth server
- A `PodcastGeneration` instance for tool execution
- Custom Starlette routes for `/health` and `/oauth2/callback`

Runs as a Gunicorn + Uvicorn process inside Docker on port 8080.

### Google OAuth provider ([`auth/provider.py`](../api/auth/provider.md))

Implements `OAuthAuthorizationServerProvider` from the MCP SDK. Delegates identity to Google but owns the full OAuth 2.1 state machine: client registration, authorization codes, access tokens, and refresh tokens. All state is serialized to JSON and written to GCS after every mutation.

### Podcast generation ([`podcast_generation.py`](../api/podcast_generation.md))

Orchestrates the two-step generation pipeline:

1. Calls `VertexClient.generate_content()` with the transcript prompt → parses the response into `(speaker, text)` turns.
2. Calls `VertexClient.synthesize_conversation()` → collects PCM frames → writes a WAV file.

### Vertex client ([`utils/vertex_client.py`](../api/utils/vertex_client.md))

Thin wrapper around three Google SDK clients:

- `genai.Client` (regional, `us-central1`) — Vertex AI TTS
- `genai.Client` (global) — Gemini transcript generation
- `anthropic.AnthropicVertex` — optional Claude routing (for models prefixed with `claude`)

## Data flows

### First-time authentication

```mermaid
sequenceDiagram
    participant C as MCP Client
    participant S as The Curator (Cloud Run)
    participant G as Google OAuth

    C->>S: POST /register (Dynamic Client Registration)
    S-->>C: client_id, client_secret
    C->>S: GET /authorize
    S-->>C: 302 → Google OAuth
    C->>G: GET /o/oauth2/v2/auth
    G-->>C: user consent page
    C->>G: approve
    G-->>S: GET /oauth2/callback?code=...
    S->>G: POST /token (exchange code)
    G-->>S: access_token
    S->>G: GET /userinfo
    G-->>S: { email }
    S->>S: verify email == ALLOWED_EMAIL
    S-->>C: 302 → redirect_uri?code=mcp_code
    C->>S: POST /token (exchange mcp_code)
    S-->>C: access_token, refresh_token
```

### Podcast generation

```mermaid
sequenceDiagram
    participant C as MCP Client
    participant S as The Curator
    participant Gemini as Vertex AI Gemini
    participant TTS as Vertex AI TTS
    participant GCS as Cloud Storage

    C->>S: create_podcast_transcript("history of radar")
    S->>Gemini: generate_content(transcript_prompt)
    Gemini-->>S: raw text (Annabelle: ... Link: ...)
    S-->>C: [(Annabelle, ...), (Link, ...), ...]

    C->>S: create_podcast_episode(title, transcript)
    loop for each turn
        S->>TTS: generate_content(turn_text, voice=Kore/Puck)
        TTS-->>S: PCM bytes
    end
    S->>S: write WAV file
    S->>GCS: upload episodes/<ts>/<title>.wav
    S-->>C: { episode_id, status: "created" }
```

## Infrastructure

All GCP resources are managed by Terraform in [`terraform/`](../infrastructure/terraform.md):

| Resource | Purpose |
| --- | --- |
| `google_cloud_run_v2_service.podcast_service` | Hosts the FastMCP server |
| `google_storage_bucket.podcast_data` | Episode audio storage (public read) |
| `google_storage_bucket.oauth_state` | OAuth state persistence (private) |
| `google_secret_manager_secret.*` | OAuth credentials injected at runtime |
| `google_service_account.podcast_service` | Cloud Run identity with scoped IAM |
