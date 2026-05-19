import time
import wave

import anthropic
from google import genai
from google.genai.types import (
    GenerateContentConfig,
    HttpOptions,
    PrebuiltVoiceConfig,
    SpeechConfig,
    VoiceConfig,
)


class VertexClient:
    def __init__(self, project: str, location: str):
        self.tts_client = genai.Client(
            vertexai=True,
            project=project,
            location=location,
            http_options=HttpOptions(api_version="v1"),
        )
        self.genai_client = genai.Client(
            vertexai=True,
            project=project,
            location="global",  # Use global for non-TTS tasks to access all models
            http_options=HttpOptions(api_version="v1"),
        )
        self.anthropic_client = anthropic.AnthropicVertex(
            project_id=project,
            region="global",
        )

    def generate_content(self, model: str, contents: str) -> str:
        if model.startswith("claude"):
            message = self.anthropic_client.messages.create(
                model=model,
                max_tokens=8096,
                messages=[{"role": "user", "content": contents}],
            )
            return message.content[0].text
        response = self.genai_client.models.generate_content(model=model, contents=contents)
        return str(response.text)

    def synthesize_conversation(
        self,
        transcript: list[tuple[str, str]],
        speaker_map: dict[str, str],
        filename: str = "conversation.wav",
    ) -> str:
        """
        # --- Example Usage ---
        my_transcript = [
            ("Eli", "Curator, are the vault logs ready for review?"),
            ("System", "Affirmative. The logs have been decrypted and are "
             "currently being indexed for your terminal."),
            ("Eli", "Excellent. Proceed with the primary sequence.")
        ]

        my_voices = {
            "Eli": "Charon",   # Deep/Human
            "System": "Puck"   # Brighter/System-like
        }
        Args:
            transcript: List of tuples [("Speaker1", "Text"), ("Speaker2", "Text")]
            speaker_map: Dict mapping speaker names to Vertex AI voice names
                        e.g. {"Eli": "Charon", "System": "Puck"}
        """
        combined_pcm = bytearray()

        print(f"🎙️ Starting synthesis for {len(transcript)} turns...")

        for i, (speaker, text) in enumerate(transcript):
            voice_name = speaker_map.get(speaker, "Charon")  # Default to Charon
            print(f"  [{i + 1}/{len(transcript)}] Synthesizing {speaker} using {voice_name}...")

            # 1. Setup the specific voice for this turn
            config = GenerateContentConfig(
                temperature=0.7,
                speech_config=SpeechConfig(
                    voice_config=VoiceConfig(
                        prebuilt_voice_config=PrebuiltVoiceConfig(voice_name=voice_name)
                    )
                ),
            )

            # 2. Add a natural pause between speakers if it's a conversation
            full_text = f"[short pause] {text}" if i > 0 else text

            try:
                response = self.tts_client.models.generate_content(
                    model="gemini-3.1-flash-tts-preview", contents=full_text, config=config
                )

                # 3. Collect raw PCM bytes
                candidates = response.candidates or []
                inline_data = candidates[0].content.parts[0].inline_data
                if inline_data and inline_data.data:
                    combined_pcm.extend(inline_data.data)

                # Optional: Small sleep to respect rate limits if the transcript is huge
                time.sleep(0.5)

            except Exception as e:
                print(f"  ❌ Error on turn {i + 1}: {e}")

        # 4. Final wrap of the combined buffer into a WAV header
        with wave.open(filename, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(24000)
            wav_file.writeframes(combined_pcm)

        print(f"✅ Conversation saved to {filename}")
        return filename
