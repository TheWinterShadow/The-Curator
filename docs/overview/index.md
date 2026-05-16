---
title: Introduction
icon: material/information-outline
---

# Introduction

The Curator is a **Model Context Protocol (MCP) server** that exposes two tools to any MCP-compatible client:

| Tool | Input | Output |
| --- | --- | --- |
| `create_podcast_transcript` | A topic string | A list of `(speaker, text)` turns |
| `create_podcast_episode` | A title + transcript | GCS path to a `.wav` audio file |

The tools are independent — generate a transcript, review and edit it, then synthesize — or chain them in a single session.

## How it works

**1. Transcript generation**

The Curator sends the topic to Google Gemini with a structured prompt that instructs the model to write a natural two-host dialogue between **Annabelle** and **Link**. Emotion tags (`[excitement]`, `[curiosity]`, `[awe]`) and pacing cues (`[short pause]`, `[fast]`, `[whispers]`) are embedded inline in the text to shape the audio output during synthesis.

**2. Audio synthesis**

Each turn in the transcript is synthesized individually using Vertex AI's `gemini-3.1-flash-tts-preview` model. Annabelle uses the **Kore** voice; Link uses **Puck**. Raw PCM frames from each turn are accumulated in memory, then written to a single 24 kHz mono `.wav` file.

**3. Storage**

The finished episode uploads to a Google Cloud Storage bucket at `episodes/<timestamp>/<title>.wav`. The GCS object name is returned to the MCP client.

## Authentication model

The server implements **MCP 2.1 OAuth** with Google as the identity provider. The flow:

1. An MCP client registers itself via Dynamic Client Registration.
2. The client is redirected to Google's authorization endpoint.
3. After the user authenticates with Google, the server verifies that the returned email matches `ALLOWED_EMAIL`.
4. If the email matches, an MCP access token and refresh token are minted and returned to the client.

OAuth state (clients, tokens, auth codes) is persisted to a private GCS bucket (`the-curator-oauth-state`) so sessions survive Cloud Run container restarts and scale-to-zero events.

## Design decisions

**Single-user by design** — The server is built for personal use. There is no multi-tenant concept, no user database, and no role system. The authorized identity is a single Google account configured at deploy time.

**Tools over resources** — Podcast generation is an expensive, stateful operation (multiple API calls, audio streaming). Exposing it as tools rather than resources gives the MCP client full control over when generation happens and makes partial results (transcript only) a first-class workflow.

**Cloud-native storage** — Audio files are not returned inline. Returning multi-megabyte WAV payloads via MCP SSE would be impractical. GCS object paths are returned instead, and the client can download or share the file out-of-band.
