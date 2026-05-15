from unittest.mock import ANY, MagicMock

from the_curator.podcast_generation import PodcastGeneration


def _make_generator(response: str) -> PodcastGeneration:
    gen = PodcastGeneration.__new__(PodcastGeneration)
    gen.vertex_client = MagicMock()
    gen.vertex_client.generate_content.return_value = response
    return gen


def test_generate_transcript_parses_both_speakers() -> None:
    gen = _make_generator("Annabelle: Hello there!\nLink: Hi Annabelle!")
    result = gen.generate_transcript("space exploration")
    assert result == [("Annabelle", "Hello there!"), ("Link", "Hi Annabelle!")]


def test_generate_transcript_preserves_audio_tags() -> None:
    response = (
        "Annabelle: [excitement] This is wild. [short pause] Ready?\n"
        "Link: [curiosity] Tell me more."
    )
    gen = _make_generator(response)
    result = gen.generate_transcript("AI")
    assert result == [
        ("Annabelle", "[excitement] This is wild. [short pause] Ready?"),
        ("Link", "[curiosity] Tell me more."),
    ]


def test_generate_transcript_ignores_non_speaker_lines() -> None:
    gen = _make_generator("Some preamble\nAnnabelle: Hello!\n\nLink: Hi!\nSome epilogue")
    result = gen.generate_transcript("AI")
    assert result == [("Annabelle", "Hello!"), ("Link", "Hi!")]


def test_generate_transcript_empty_response_returns_empty_list() -> None:
    gen = _make_generator("")
    result = gen.generate_transcript("anything")
    assert result == []


def test_generate_podcast_passes_transcript_to_vertex_client() -> None:
    gen = PodcastGeneration.__new__(PodcastGeneration)
    gen.vertex_client = MagicMock()
    gen.vertex_client.synthesize_conversation.return_value = "podcast_abc.wav"

    transcript = [("Annabelle", "Hello"), ("Link", "Hi")]
    result = gen.generate_podcast(transcript)

    gen.vertex_client.synthesize_conversation.assert_called_once_with(
        transcript,
        {"Annabelle": "Kore", "Link": "Puck"},
        ANY,
    )
    assert result == "podcast_abc.wav"
