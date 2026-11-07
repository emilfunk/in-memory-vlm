"""Unit tests for in-memory JPEG frame parsing and deduplication."""

import io
from PIL import Image
from in_memory_vlm.core.frame_extractor import (
    calculate_frame_difference,
    filter_keyframes,
    parse_mjpeg_stream,
)


def _create_dummy_jpeg(color: tuple) -> bytes:
    img = Image.new("RGB", (64, 64), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_parse_mjpeg_stream():
    # Create two synthetic JPEGs
    jpeg1 = _create_dummy_jpeg((255, 0, 0))
    jpeg2 = _create_dummy_jpeg((0, 255, 0))

    # Concatenate them as a raw MJPEG stream with garbage between/before
    stream = b"GARBAGE_START" + jpeg1 + b"TRANSIT_GARBAGE" + jpeg2 + b"GARBAGE_END"
    parsed = parse_mjpeg_stream(stream)

    assert len(parsed) == 2
    assert parsed[0].startswith(b"\xff\xd8")
    assert parsed[0].endswith(b"\xff\xd9")
    assert parsed[1].startswith(b"\xff\xd8")
    assert parsed[1].endswith(b"\xff\xd9")


def test_calculate_frame_difference():
    img_red1 = Image.new("RGB", (64, 64), (255, 0, 0))
    img_red2 = Image.new("RGB", (64, 64), (255, 0, 0))
    img_blue = Image.new("RGB", (64, 64), (0, 0, 255))

    diff_same = calculate_frame_difference(img_red1, img_red2)
    diff_diff = calculate_frame_difference(img_red1, img_blue)

    assert diff_same == 0.0
    assert diff_diff > 0.4


def test_filter_keyframes_deduplication():
    red_frame = _create_dummy_jpeg((255, 0, 0))
    green_frame = _create_dummy_jpeg((0, 255, 0))
    blue_frame = _create_dummy_jpeg((0, 0, 255))

    # Stream of identical frames followed by changes
    raw_frames = [red_frame] * 10 + [green_frame] * 10 + [blue_frame] * 10
    selected = filter_keyframes(raw_frames, max_frames=5, min_diff_threshold=0.1)

    # Dedup should collapse repeated red/green/blue frames
    assert len(selected) >= 3
    assert len(selected) <= 5
