"""Unit tests for in-memory audio extraction."""

import asyncio
import shutil
import pytest
from in_memory_vlm.core.audio_extractor import extract_audio_stream_in_memory


@pytest.mark.asyncio
async def test_extract_audio_empty():
    res = await extract_audio_stream_in_memory(b"")
    assert res is None


@pytest.mark.asyncio
async def test_extract_audio_corrupt_data():
    res = await extract_audio_stream_in_memory(b"NOT_A_VALID_MEDIA_STREAM")
    assert res is None


@pytest.mark.asyncio
async def test_extract_audio_synthetic_stream():
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg binary not available")

    # Generate 0.5s of synthetic WAV tone via ffmpeg
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=800:duration=0.5",
        "-f", "wav", "pipe:1",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    raw_wav, _ = await proc.communicate()
    assert len(raw_wav) > 0

    # Extract & resample to 16kHz mono in RAM
    result_wav = await extract_audio_stream_in_memory(raw_wav, sample_rate=16000)
    assert result_wav is not None
    assert result_wav.startswith(b"RIFF")
    assert b"WAVE" in result_wav[:16]
