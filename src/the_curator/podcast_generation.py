import os
import tempfile

from the_curator.utils.vertex_client import VertexClient


class PodcastGeneration:
    def __init__(self) -> None:
        self.vertex_client = VertexClient(
            project=os.environ.get("GOOGLE_CLOUD_PROJECT", "the-curator"), location="us-central1"
        )

    def generate_transcript(self, topic: str) -> list[tuple[str, str]]:
        response = self.vertex_client.generate_content(
            model="gemini-3.1-pro-preview",
            contents=(
                f"Generate an engaging podcast transcript on the topic: {topic}.\n\n"
                "The podcast features host Annabelle and co-host Link "
                "having a natural, informative conversation. "
                "They should explore the topic with genuine curiosity, "
                "banter, and energy — not just recite facts.\n\n"
                "Formatting rules (follow exactly):\n"
                "- Each line must start with exactly 'Annabelle:' or 'Link:' "
                "followed by a space and the spoken text.\n"
                "- No other formatting, headers, stage directions, or labels.\n\n"
                "Audio expression tags — embed these inline within the spoken text "
                "to add emotion, pacing, and texture:\n"
                "Emotion: [determination], [enthusiasm], [adoration], [interest], "
                "[awe], [admiration], [nervousness], [frustration], [excitement], "
                "[curiosity], [hope], [annoyance], [amusement], [aggression], "
                "[tension], [agitation], [confusion], [anger], [positive], [neutral], [negative]\n"
                "Non-verbal: [laughs], [whispers]\n"
                "Pacing: [slow], [fast], [short pause], [long pause]\n\n"
                "Use these tags naturally and liberally — they shape how the audio sounds. "
                "For example: 'Annabelle: [excitement] Okay so this is the part "
                "that blew my mind. [short pause] Ready?'\n\n"
                "Generate a full episode — at least 15–20 turns."
            ),
        )
        turns: list[tuple[str, str]] = []
        for line in response.splitlines():
            line = line.strip()
            if line.startswith("Annabelle:"):
                turns.append(("Annabelle", line[len("Annabelle:") :].strip()))
            elif line.startswith("Link:"):
                turns.append(("Link", line[len("Link:") :].strip()))
        return turns

    def generate_podcast(self, transcript: list[tuple[str, str]]) -> str:
        speaker_map = {"Annabelle": "Kore", "Link": "Puck"}
        _, filename = tempfile.mkstemp(suffix=".wav", prefix="podcast_")
        return self.vertex_client.synthesize_conversation(transcript, speaker_map, filename)
