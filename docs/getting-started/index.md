---
title: Quick Start
icon: material/rocket-launch
---

# Quick Start

This guide gets you from zero to a generated podcast episode in about 10 minutes.

## Prerequisites

- A Google Cloud project with billing enabled
- A Google OAuth 2.0 client ID and secret ([create one](https://console.cloud.google.com/apis/credentials))
- The Vertex AI API enabled in your project
- An MCP-compatible client (Claude Desktop, Cursor, Zed, or `mcp-remote`)

## 1. Deploy to Cloud Run

The fastest path is deploying via the CI/CD pipeline. Fork the repo, configure secrets in GitHub, and push to `main` — the [Deploy workflow](https://github.com/TheWinterShadow/The-Curator/actions/workflows/deploy.yml) handles the rest.

See [Infrastructure → Terraform](../infrastructure/terraform.md) for the full setup.

After deployment, note your Cloud Run service URL — you'll need it in the next step.

## 2. Connect an MCP client

=== ":material-chat: Claude Desktop"

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

    Restart Claude Desktop. On first use, a browser window will open for Google OAuth.

=== ":material-cursor-default: Cursor / Zed"

    Point your client at `https://your-cloud-run-url/sse` as an SSE MCP server. Consult your client's docs for the exact configuration format.

=== ":material-console: mcp-remote (CLI)"

    ```bash
    npx mcp-remote https://your-cloud-run-url/sse
    ```

## 3. Generate a transcript

In your MCP client, call:

```
Create a podcast transcript about the Voyager probe's journey beyond the solar system.
```

The server calls Gemini and returns a list of `(speaker, text)` turns. Review the transcript — edit it if you like — before proceeding.

## 4. Synthesize the episode

```
Create a podcast episode titled "Voyager" using the transcript above.
```

The server synthesizes each turn with Vertex AI TTS, writes a `.wav` file, and uploads it to GCS. You'll get back a GCS path like `episodes/2026-05-16_18-30/Voyager.wav`.

## What's next?

- [MCP Clients](mcp-clients.md) — connecting additional clients and troubleshooting OAuth
- [Configuration](../configuration/index.md) — environment variables reference
- [Infrastructure](../infrastructure/index.md) — Terraform setup and CI/CD pipeline
