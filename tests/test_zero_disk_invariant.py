"""Verification of strict zero-disk invariant across all in-memory pipelines."""

import builtins
import io
import os
from PIL import Image
import pytest
from in_memory_vlm.core.frame_extractor import (
    calculate_frame_difference,
    filter_keyframes,
    parse_mjpeg_stream,
)
from in_memory_vlm.core.audio_extractor import extract_audio_stream_in_memory


def test_zero_disk_frame_extraction(monkeypatch):
    """Confirm no file writes occur during MJPEG parsing and keyframe filtering."""
    written_files = []
    orig_open = builtins.open

    def guarded_open(file, mode="r", *args, **kwargs):
        if any(m in mode for m in ("w", "a", "+")):
            written_files.append(str(file))
        return orig_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded_open)

    # Generate synthetic in-memory frames
    frames_raw = []
    for c in [(255, 0, 0), (0, 255, 0), (0, 0, 255)]:
        img = Image.new("RGB", (64, 64), color=c)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        frames_raw.append(buf.getvalue())

    mjpeg_stream = b"".join(frames_raw)
    parsed = parse_mjpeg_stream(mjpeg_stream)
    assert len(parsed) == 3

    selected = filter_keyframes(parsed, max_frames=2)
    assert len(selected) <= 2

    # Verify zero files opened for writing
    assert len(written_files) == 0, f"Violated zero-disk invariant! Files written: {written_files}"
