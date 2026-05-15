from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import the_curator.main as main_module
from the_curator.main import app, create_podcast_episode, create_podcast_transcript


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"service": "the-curator", "status": "ok"}


def test_create_podcast_transcript_delegates_to_generator(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_gen = MagicMock()
    mock_gen.generate_transcript.return_value = [("Annabelle", "Hello"), ("Link", "Hi")]
    monkeypatch.setattr(main_module, "generator", mock_gen)

    result = create_podcast_transcript("artificial intelligence")

    mock_gen.generate_transcript.assert_called_once_with("artificial intelligence")
    assert result == [("Annabelle", "Hello"), ("Link", "Hi")]


def test_create_podcast_episode(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_gen = MagicMock()
    mock_gen.generate_podcast.return_value = "/tmp/podcast.wav"
    monkeypatch.setattr(main_module, "generator", mock_gen)

    transcript = [("Annabelle", "Hello"), ("Link", "Hi")]
    result = create_podcast_episode("Test Episode", transcript)

    mock_gen.generate_podcast.assert_called_once_with(transcript)
    assert result["status"] == "created"
