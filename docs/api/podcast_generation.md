---
title: Podcast Generation
icon: material/microphone
---

# Podcast Generation

Orchestrates the two-step pipeline: transcript generation via Gemini and audio synthesis via Vertex AI TTS.

## Transcript prompt

The prompt instructs Gemini to write a dialogue between two hosts:

- **Annabelle** — the primary host
- **Link** — the co-host

Emotion tags and pacing cues are embedded inline in the text and interpreted by the TTS model:

**Emotion tags:** `[determination]`, `[enthusiasm]`, `[awe]`, `[curiosity]`, `[excitement]`, `[amusement]`, `[frustration]`, `[nervousness]`, and more.

**Non-verbal:** `[laughs]`, `[whispers]`

**Pacing:** `[slow]`, `[fast]`, `[short pause]`, `[long pause]`

## Voice mapping

| Host | Vertex AI voice |
| --- | --- |
| Annabelle | Kore |
| Link | Puck |

Both voices use the `gemini-3.1-flash-tts-preview` model. Each turn is synthesized separately and the PCM frames are concatenated before writing the final WAV file.

## Audio format

| Property | Value |
| --- | --- |
| Channels | 1 (mono) |
| Sample width | 2 bytes (16-bit PCM) |
| Frame rate | 24,000 Hz |
| Format | WAV |

## Module reference

::: the_curator.podcast_generation
