"""Unit tests for in-memory stream pipe orchestrator."""

from unittest.mock import patch
import pytest
from in_memory_vlm.core.stream_pipe import StreamPipeError, extract_media_in_memory


@pytest.mark.asyncio
async def test_stream_pipe_missing_ytdlp():
    with patch("shutil.which", side_effect=lambda bin_name: None if bin_name == "yt-dlp" else "/usr/bin/ffmpeg"):
        with pytest.raises(StreamPipeError, match="yt-dlp binary not found"):
            await extract_media_in_memory("https://example.com/video")


@pytest.mark.asyncio
async def test_stream_pipe_missing_ffmpeg():
    with patch("shutil.which", side_effect=lambda bin_name: "/usr/bin/yt-dlp" if bin_name == "yt-dlp" else None):
        with pytest.raises(StreamPipeError, match="ffmpeg binary not found"):
            await extract_media_in_memory("https://example.com/video")
