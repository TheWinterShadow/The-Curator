---
title: Vertex Client
icon: simple/googlecloud
---

# Vertex Client

Thin wrapper around three Google SDK clients, providing a unified interface for text generation and multi-speaker audio synthesis.

## Clients

| Client | SDK | Purpose |
| --- | --- | --- |
| `tts_client` | `google.genai` (regional `us-central1`) | Vertex AI TTS via `gemini-3.1-flash-tts-preview` |
| `genai_client` | `google.genai` (global) | Gemini transcript generation |
| `anthropic_client` | `anthropic.AnthropicVertex` (global) | Optional Claude routing |

The regional/global split exists because Vertex AI TTS is only available in certain regional endpoints, while Gemini model access benefits from the global endpoint.

## Model routing

`generate_content()` routes automatically:

- Models prefixed with `claude` → `anthropic_client` (AnthropicVertex)
- All other models → `genai_client` (Google GenAI)

This lets `PodcastGeneration` swap between Gemini and Claude for transcript generation by changing the `model` argument.

## Audio synthesis

`synthesize_conversation()` synthesizes each `(speaker, text)` turn individually:

1. Looks up the voice name from `speaker_map`.
2. Prepends `[short pause]` to all turns after the first (natural inter-speaker breathing room).
3. Calls the TTS model with `temperature=0.7` and a `PrebuiltVoiceConfig`.
4. Extracts raw PCM bytes from `response.candidates[0].content.parts[0].inline_data`.
5. Accumulates all PCM frames, then writes a single WAV file.

A 500 ms sleep between turns respects TTS API rate limits.

## Module reference

::: the_curator.utils.vertex_client
