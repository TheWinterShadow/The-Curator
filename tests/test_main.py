from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import the_curator.main as main_module
from the_curator.main import app, create_podcast_episode


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"service": "the-curator", "status": "ok"}


def test_create_podcast_episode(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_gen = MagicMock()
    mock_gen.generate_podcast.return_value = "/tmp/podcast.wav"
    monkeypatch.setattr(main_module, "generator", mock_gen)
    monkeypatch.setattr(main_module.storage, "Client", MagicMock())
    monkeypatch.setattr(main_module.os.path, "getsize", MagicMock(return_value=1024))

    result = create_podcast_episode("artificial intelligence", "Test Episode")

    mock_gen.generate_podcast.assert_called_once()
    assert result["status"] == "created"
