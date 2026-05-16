---
title: The Curator
description: An MCP server that generates AI-powered podcasts on any topic, in minutes.
icon: fontawesome/solid/scroll
hide:
  - navigation
  - toc
---

# The Curator :fontawesome-solid-scroll:

**AI-powered podcast generation via MCP** — give it a topic, get a fully voiced episode back.

[![Deploy](https://img.shields.io/github/actions/workflow/status/TheWinterShadow/The-Curator/deploy.yml?branch=main&logo=github&label=Deploy)](https://github.com/TheWinterShadow/The-Curator/actions/workflows/deploy.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/TheWinterShadow/The-Curator/blob/main/LICENSE)

---

<div class="grid cards" markdown>

-   :simple-googlegemini: **Write the script**

    ---

    Google Gemini writes a natural, multi-turn dialogue between hosts **Annabelle** and **Link** — complete with emotion tags, pacing cues, and genuine banter.

-   :material-microphone: **Synthesize the audio**

    ---

    Vertex AI TTS brings the transcript to life with two distinct voices. Raw PCM frames are stitched turn-by-turn into a single `.wav` file.

-   :material-cloud-upload: **Store and serve**

    ---

    Episodes upload directly to **Google Cloud Storage**. Share the GCS URL or pipe it into your own podcast feed.

-   :material-shield-lock: **Secure by default**

    ---

    Single-user **Google OAuth 2.0** via MCP 2.1. Only your Google account can authenticate; session state persists across container restarts.

</div>

---

## Quick start

=== ":material-chat: Claude Desktop"

    Add to `claude_desktop_config.json`:

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

    On first use, Claude will open a browser to complete Google OAuth. After that, use the tools directly:

    > *"Create a podcast transcript about the history of radar."*

=== ":fontawesome-brands-docker: Docker"

    ```bash
    docker build -t the-curator .

    docker run --rm -p 8080:8080 \
      -e GOOGLE_CLIENT_ID=your-client-id \
      -e GOOGLE_CLIENT_SECRET=your-client-secret \
      -e ALLOWED_EMAIL=you@example.com \
      -e SERVER_URL=http://localhost:8080 \
      the-curator
    ```

=== ":fontawesome-brands-python: Local"

    ```bash
    pipx install hatch

    export GOOGLE_CLIENT_ID=...
    export GOOGLE_CLIENT_SECRET=...
    export ALLOWED_EMAIL=you@example.com
    export SERVER_URL=http://localhost:8000

    hatch run start
    ```

---

## Where to go next

<div class="grid cards" markdown>

-   [**:material-information-outline: Overview**](overview/index.md){ .md-button }

    How The Curator works and the design decisions behind it.

-   [**:material-rocket-launch: Getting Started**](getting-started/index.md){ .md-button .md-button--primary }

    Connect an MCP client and generate your first episode in minutes.

-   [**:material-tune: Configuration**](configuration/index.md){ .md-button }

    Environment variables and runtime options, fully documented.

-   [**:material-server: Infrastructure**](infrastructure/index.md){ .md-button }

    Docker, Terraform, GCP setup, and CI/CD.

-   [**:material-code-tags: API Reference**](api/main.md){ .md-button }

    Every class and function, fully documented.

</div>
