"""In-memory JPEG frame extractor and deduplicator."""

from __future__ import annotations

import io
from typing import List, Tuple
from PIL import Image


def parse_mjpeg_stream(stream_bytes: bytes) -> List[bytes]:
    """
    Extracts individual JPEG byte blocks from a continuous MJPEG byte stream in memory.
    JPEG images start with SOI (0xFF, 0xD8) and end with EOI (0xFF, 0xD9).
    """
    frames: List[bytes] = []
    start = 0
    stream_len = len(stream_bytes)

    while start < stream_len:
        soi = stream_bytes.find(b"\xff\xd8", start)
        if soi == -1:
            break
        eoi = stream_bytes.find(b"\xff\xd9", soi + 2)
        if eoi == -1:
            break
        frame_data = stream_bytes[soi : eoi + 2]
        frames.append(frame_data)
        start = eoi + 2

    return frames


def calculate_frame_difference(img_a: Image.Image, img_b: Image.Image) -> float:
    """
    Computes normalized histogram difference between two images in memory.
    Returns a score between 0.0 (identical) and 1.0 (completely distinct).
    """
    thumb_a = img_a.resize((64, 64)).convert("L")
    thumb_b = img_b.resize((64, 64)).convert("L")

    hist_a = thumb_a.histogram()
    hist_b = thumb_b.histogram()

    # Sum of absolute differences normalized by total pixels (64*64 = 4096)
    diff = sum(abs(a - b) for a, b in zip(hist_a, hist_b))
    max_possible_diff = 2 * (64 * 64)
    return diff / max_possible_diff


def filter_keyframes(
    raw_frames: List[bytes],
    max_frames: int = 20,
    min_diff_threshold: float = 0.15,
) -> List[Tuple[int, bytes]]:
    """
    Filters raw frames using scene-aware difference heuristics.
    Returns a list of (index, jpeg_bytes) representing key transitions.
    """
    if not raw_frames:
        return []

    if len(raw_frames) <= max_frames:
        return list(enumerate(raw_frames))

    selected: List[Tuple[int, bytes]] = [(0, raw_frames[0])]
    try:
        last_image = Image.open(io.BytesIO(raw_frames[0]))
    except Exception:
        last_image = None

    for idx in range(1, len(raw_frames)):
        frame_bytes = raw_frames[idx]
        try:
            current_image = Image.open(io.BytesIO(frame_bytes))
            if last_image is not None:
                diff = calculate_frame_difference(last_image, current_image)
                if diff >= min_diff_threshold:
                    selected.append((idx, frame_bytes))
                    last_image = current_image
            else:
                selected.append((idx, frame_bytes))
                last_image = current_image
        except Exception:
            continue

        if len(selected) >= max_frames:
            break

    # If heuristic was too strict, fallback to uniform stride
    if len(selected) < min(5, len(raw_frames)):
        step = max(1, len(raw_frames) // max_frames)
        selected = [(i, raw_frames[i]) for i in range(0, len(raw_frames), step)[:max_frames]]

    return selected
