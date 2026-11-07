"""Unit tests for VLM payload formatting and client initialization."""

import json
from unittest.mock import MagicMock, patch
import pytest
from in_memory_vlm.vlm.gemini_client import GeminiClient
from in_memory_vlm.vlm.claude_client import ClaudeClient


def test_gemini_client_missing_key():
    client = GeminiClient(api_key=None)
    # Clear env var if set
    client.client = None
    with pytest.raises(RuntimeError, match="Gemini API key is not configured"):
        client.analyze_media(frames=[b"dummy_frame"])


def test_claude_client_missing_key():
    client = ClaudeClient(api_key=None)
    client.api_key = None
    with pytest.raises(RuntimeError, match="Anthropic API key is not configured"):
        client.analyze_media(frames=[b"dummy_frame"])


def test_gemini_client_payload_formatting():
    client = GeminiClient(api_key="mock-api-key")
    mock_resp = MagicMock()
    mock_resp.text = "Mock analysis result"
    mock_resp.usage_metadata.prompt_token_count = 120
    mock_resp.usage_metadata.candidates_token_count = 45
    mock_resp.usage_metadata.total_token_count = 165
    client.client.models.generate_content = MagicMock(return_value=mock_resp)

    res = client.analyze_media(
        frames=[(0, b"\xff\xd8fakeframe1\xff\xd9"), b"\xff\xd8fakeframe2\xff\xd9"],
        audio_wav=b"RIFFmockwavdata",
        context_text="Mock tweet text",
        prompt="Describe the code shown",
    )

    assert res["text"] == "Mock analysis result"
    assert res["usage"]["total_token_count"] == 165
    assert res["model"] == "gemini-2.5-flash"

    # Verify generate_content arguments
    call_args = client.client.models.generate_content.call_args[1]
    assert call_args["model"] == "gemini-2.5-flash"
    contents = call_args["contents"]
    assert contents[0] == "Describe the code shown"
    assert "Mock tweet text" in contents[1]


def test_claude_client_payload_formatting():
    client = ClaudeClient(api_key="mock-anthropic-key")
    mock_http_resp = MagicMock()
    mock_http_resp.read.return_value = json.dumps({
        "content": [{"type": "text", "text": "Claude visual analysis result"}],
        "usage": {"input_tokens": 80, "output_tokens": 40}
    }).encode("utf-8")
    mock_http_resp.__enter__.return_value = mock_http_resp

    with patch("urllib.request.urlopen", return_value=mock_http_resp) as mock_urlopen:
        res = client.analyze_media(
            frames=[b"\xff\xd8fakeframe\xff\xd9"],
            context_text="Mock LinkedIn post",
            prompt="Summarize this",
        )

        assert res["text"] == "Claude visual analysis result"
        assert res["usage"]["input_tokens"] == 80
        assert res["model"] == "claude-3-7-sonnet-20250219"

        req = mock_urlopen.call_args[0][0]
        assert req.headers["X-api-key"] == "mock-anthropic-key"
        payload = json.loads(req.data.decode("utf-8"))
        assert payload["model"] == "claude-3-7-sonnet-20250219"
        msg_content = payload["messages"][0]["content"]
        assert any(b.get("type") == "image" for b in msg_content)
