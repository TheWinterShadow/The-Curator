from unittest.mock import MagicMock

from the_curator.utils.vertex_client import VertexClient


def _make_client() -> VertexClient:
    client = VertexClient.__new__(VertexClient)
    client.genai_client = MagicMock()
    client.anthropic_client = MagicMock()
    return client


def test_generate_content_routes_claude_to_anthropic_client() -> None:
    client = _make_client()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="transcript output")]
    client.anthropic_client.messages.create.return_value = mock_message

    result = client.generate_content("claude-opus-4-7", "generate a transcript")

    client.anthropic_client.messages.create.assert_called_once_with(
        model="claude-opus-4-7",
        max_tokens=8096,
        messages=[{"role": "user", "content": "generate a transcript"}],
    )
    client.genai_client.models.generate_content.assert_not_called()
    assert result == "transcript output"


def test_generate_content_routes_gemini_to_genai_client() -> None:
    client = _make_client()
    mock_response = MagicMock()
    mock_response.text = "gemini output"
    client.genai_client.models.generate_content.return_value = mock_response

    result = client.generate_content("gemini-2.0-flash-001", "generate a transcript")

    client.genai_client.models.generate_content.assert_called_once()
    client.anthropic_client.messages.create.assert_not_called()
    assert result == "gemini output"


def test_generate_content_claude_prefix_matching() -> None:
    client = _make_client()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="response")]
    client.anthropic_client.messages.create.return_value = mock_message

    for model in ["claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5"]:
        client.anthropic_client.reset_mock()
        client.generate_content(model, "prompt")
        client.anthropic_client.messages.create.assert_called_once()
