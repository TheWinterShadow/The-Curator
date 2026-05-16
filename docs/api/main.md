---
title: Server
icon: material/server
---

# Server

The entry point for the FastMCP server. Defines the two MCP tools and wires together authentication, storage, and generation.

## MCP tools

### `create_podcast_transcript`

```python
@mcp.tool()
def create_podcast_transcript(topic: str) -> list[tuple[str, str]]
```

Generates a podcast transcript on the given topic.

Calls `PodcastGeneration.generate_transcript()`, which sends a structured prompt to Gemini and parses the response into `(speaker, text)` turns.

**Arguments:**

| Argument | Type | Description |
| --- | --- | --- |
| `topic` | `str` | The topic for the podcast episode. Any string works — be as specific or general as you like. |

**Returns:** A list of `(speaker, text)` tuples. Speaker is either `"Annabelle"` or `"Link"`.

**Example return value:**

```python
[
    ("Annabelle", "[excitement] Okay so today we're diving into Voyager 1..."),
    ("Link", "[curiosity] Right, and what always gets me is just how far it's traveled..."),
    ...
]
```

---

### `create_podcast_episode`

```python
@mcp.tool()
def create_podcast_episode(title: str, transcript: list[tuple[str, str]]) -> dict[str, str]
```

Synthesizes a transcript into audio and uploads it to GCS.

Calls `PodcastGeneration.generate_podcast()` to produce a `.wav` file, then uploads it to the `GCS_BUCKET_NAME` bucket at `episodes/<timestamp>/<title>.wav`.

**Arguments:**

| Argument | Type | Description |
| --- | --- | --- |
| `title` | `str` | Episode title, used as the filename. Spaces are replaced with underscores. |
| `transcript` | `list[tuple[str, str]]` | Output of `create_podcast_transcript`. |

**Returns:** `{"episode_id": "<filename>", "status": "created"}`

---

## HTTP endpoints

| Path | Method | Description |
| --- | --- | --- |
| `/sse` | `GET` | MCP SSE transport. Primary client entrypoint. |
| `/health` | `GET` | Health check — returns `{"service": "the-curator", "status": "ok"}` |
| `/oauth2/callback` | `GET` | Google OAuth callback. Handled by `GoogleOAuthProvider`. |
| `/.well-known/oauth-authorization-server` | `GET` | OAuth 2.0 server metadata (MCP discovery). |
| `/register` | `POST` | Dynamic Client Registration. |
| `/authorize` | `GET` | MCP authorization endpoint — redirects to Google. |
| `/token` | `POST` | Token endpoint — exchanges codes and refreshes tokens. |
| `/revoke` | `POST` | Token revocation endpoint. |

## Module reference

::: the_curator.main
