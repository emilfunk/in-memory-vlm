"""Unit tests for CLI argument parsing."""

from in_memory_vlm.cli import parse_args


def test_parse_args_defaults():
    args = parse_args(["https://www.youtube.com/watch?v=12345678901"])
    assert args.url == "https://www.youtube.com/watch?v=12345678901"
    assert args.mode == "auto"
    assert args.model == "gemini"
    assert args.max_frames == 15
    assert args.cdp_port == 9222
    assert not args.json


def test_parse_args_custom():
    args = parse_args([
        "https://instagram.com/reel/abcde",
        "--mode", "browser",
        "--model", "claude",
        "--max-frames", "25",
        "--json",
        "--cookies", "chrome",
    ])
    assert args.url == "https://instagram.com/reel/abcde"
    assert args.mode == "browser"
    assert args.model == "claude"
    assert args.max_frames == 25
    assert args.json
    assert args.cookies_browser == "chrome"
