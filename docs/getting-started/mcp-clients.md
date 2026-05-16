---
title: MCP Clients
icon: material/connection
---

# MCP Clients

The Curator uses MCP's **SSE transport** with **OAuth 2.1** authentication. Any client that supports `mcp-remote` or native MCP SSE can connect.

## Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "the-curator": {
      "command": "npx",
      "args": ["mcp-remote", "https://your-cloud-run-url/sse"]
    }
  }
}
```

Restart Claude Desktop. The first time a tool is invoked, `mcp-remote` opens a browser window and walks you through Google OAuth. After authentication, the access token is cached locally and refreshed automatically.

## Cursor

In Cursor settings, add an MCP server with SSE transport pointing at `https://your-cloud-run-url/sse`. If Cursor doesn't support OAuth natively, wrap it with `mcp-remote` as above.

## mcp-remote (CLI)

For scripting or testing:

```bash
npx mcp-remote https://your-cloud-run-url/sse
```

On first run, a browser opens for OAuth. The token is stored in `~/.mcp-auth/`.

## Troubleshooting OAuth

**"Invalid or expired OAuth state"** — The 10-minute window for completing the OAuth flow expired. Restart the authorization flow.

**"Email is not authorized"** — The Google account you authenticated with doesn't match `ALLOWED_EMAIL`. Re-check the environment variable on the Cloud Run service.

**"Failed to load OAuth state from GCS"** — The Cloud Run service account doesn't have `storage.objectAdmin` on the OAuth state bucket. Check IAM bindings in Terraform.

**Token expired mid-session** — Access tokens last 1 hour; refresh tokens last 30 days. `mcp-remote` handles token refresh automatically. If refresh fails, re-authenticate by deleting `~/.mcp-auth/` and reconnecting.

## Checking registered clients

OAuth client registrations are persisted in the `the-curator-oauth-state` GCS bucket as `oauth-state/state.json`. Inspect it with:

```bash
gcloud storage cat gs://the-curator-oauth-state/oauth-state/state.json | jq '.clients | keys'
```
