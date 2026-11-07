"""In-memory audio extraction and conversion to WAV buffers."""

from __future__ import annotations

import asyncio
from typing import Optional


async def extract_audio_stream_in_memory(
    stream_input: bytes,
    sample_rate: int = 16000,
) -> Optional[bytes]:
    """
    Feeds a raw media byte buffer into ffmpeg via stdin pipe and extracts
    a compact 16kHz mono WAV buffer directly to memory via stdout pipe.
    """
    if not stream_input:
        return None

    cmd = [
        "ffmpeg",
        "-loglevel", "error",
        "-i", "pipe:0",
        "-vn",
        "-ar", str(sample_rate),
        "-ac", "1",
        "-f", "wav",
        "pipe:1"
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        wav_bytes, err = await proc.communicate(input=stream_input)
        if proc.returncode == 0 and wav_bytes:
            return wav_bytes
    except Exception:
        return None

    return None
