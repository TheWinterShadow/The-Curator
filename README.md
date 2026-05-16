# The Curator

![The Curator](assets/curator.png)

> An MCP server that generates AI-powered podcasts — on any topic, in minutes.

The Curator uses Google Gemini to write a natural, multi-turn podcast transcript and Vertex AI TTS to synthesize it into audio. It exposes two MCP tools that any MCP-compatible client (Claude Desktop, Zed, Cursor, etc.) can call directly.

---

## MCP Tools

| Tool | Description |
| --- | --- |
| `create_podcast_transcript` | Generates a podcast transcript between hosts Annabelle and Link on any topic |
| `create_podcast_episode` | Synthesizes a transcript into a `.wav` audio file and uploads it to GCS |

## Tech Stack

- **Python 3.12**
- **FastMCP** — MCP server framework
- **Google Gemini** (via Vertex AI) — transcript generation
- **Vertex AI TTS** — multi-speaker audio synthesis
- **Google OAuth 2.0** — single-user authentication for MCP clients
- **Google Cloud Storage** — episode and OAuth state storage
- **Cloud Run** — serverless hosting
- **Hatch** — environment and task management
- **Ruff, MyPy, Pytest** — code quality

## Project Structure

```text
.
├── Dockerfile
├── pyproject.toml
├── src/
│   └── the_curator/
│       ├── main.py                  # FastMCP server, OAuth routes
│       ├── podcast_generation.py    # Transcript + audio synthesis
│       ├── auth/
│       │   └── provider.py          # Google OAuth provider
│       └── utils/
│           └── vertex_client.py     # Vertex AI client wrapper
├── terraform/                       # GCP infra (Cloud Run, GCS, Secret Manager)
└── tests/
```

## Local Development

1. Install Hatch:

   ```bash
   pipx install hatch
   ```

2. Set required environment variables:

   ```bash
   export GOOGLE_CLIENT_ID=...
   export GOOGLE_CLIENT_SECRET=...
   export ALLOWED_EMAIL=you@example.com
   export SERVER_URL=http://localhost:8000
   ```

3. Run the server:

   ```bash
   hatch run start
   ```

4. Run checks:

   ```bash
   hatch run check
   ```

## Run with Docker

```bash
docker build -t the-curator .
docker run --rm -p 8080:8080 \
  -e GOOGLE_CLIENT_ID=... \
  -e GOOGLE_CLIENT_SECRET=... \
  -e ALLOWED_EMAIL=you@example.com \
  -e SERVER_URL=http://localhost:8080 \
  the-curator
```

## Deploy to GCP

Infrastructure is managed with Terraform. The Cloud Run service pulls credentials from Secret Manager.

```bash
cd terraform
terraform init
terraform apply \
  -var="podcast_service_image_uri=gcr.io/the-curator-496412/the-curator:latest" \
  -var="google_client_id=..." \
  -var="google_client_secret=..." \
  -var="allowed_email=you@example.com" \
  -var="server_url=https://your-cloud-run-url"
```

A GitHub Actions workflow handles image builds and deploys on push to `main`.

## Endpoints

| Path | Description |
| --- | --- |
| `/health` | Health check |
| `/sse` | MCP SSE transport (client entry) |
| `/.well-known/oauth-authorization-server` | OAuth discovery |
| `/oauth2/callback` | Google OAuth callback |
