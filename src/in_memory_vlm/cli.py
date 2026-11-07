"""Command line interface for in-memory-vlm."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Optional

from in_memory_vlm.browser.cdp_client import extract_from_browser_tab
from in_memory_vlm.core.stream_pipe import extract_media_in_memory
from in_memory_vlm.vlm.claude_client import ClaudeClient
from in_memory_vlm.vlm.gemini_client import GeminiClient


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        prog="vlm-watch",
        description="Zero-disk in-memory media interception and VLM reasoning CLI.",
    )
    parser.add_argument("url", help="Media URL to inspect (YouTube, Instagram, LinkedIn, X, etc.)")
    parser.add_argument(
        "--mode",
        choices=["auto", "pipe", "browser"],
        default="auto",
        help="Ingestion mode: auto selects browser for IG/LinkedIn and pipe for YouTube/X.",
    )
    parser.add_argument(
        "--cookies",
        "--cookies-from-browser",
        dest="cookies_browser",
        default=None,
        help="Browser name to extract cookies from for yt-dlp (e.g. 'chrome', 'brave', 'safari').",
    )
    parser.add_argument(
        "--cdp-port",
        type=int,
        default=9222,
        help="CDP debugging port for browser DOM extraction (default: 9222).",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=15,
        help="Maximum keyframes to extract (default: 15).",
    )
    parser.add_argument(
        "--model",
        choices=["gemini", "claude"],
        default="gemini",
        help="VLM backend to query (default: gemini).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print structured JSON output instead of plain text.",
    )
    parser.add_argument(
        "--prompt",
        default=None,
        help="Custom prompt for the VLM analysis.",
    )
    return parser.parse_args(args)


async def run_pipeline(args) -> dict:
    url = args.url
    mode = args.mode

    if mode == "auto":
        # Heuristic: Instagram and LinkedIn are best handled in the live browser DOM
        if "instagram.com" in url or "linkedin.com" in url:
            mode = "browser"
        else:
            mode = "pipe"

    frames = []
    audio_wav = None
    post_text = None

    if mode == "browser":
        # Extract via CDP from live browser tab
        browser_data = await extract_from_browser_tab(
            cdp_port=args.cdp_port,
            target_url=url,
            num_frames=args.max_frames,
        )
        frames = [item["base64_jpeg"] for item in browser_data.get("keyframes", [])]
        post_text = browser_data.get("post_text")
    else:
        # Extract via yt-dlp / ffmpeg pipe in memory
        stream_data = await extract_media_in_memory(
            url=url,
            cookies_browser=args.cookies_browser,
            max_frames=args.max_frames,
            include_audio=(args.model == "gemini"),
        )
        frames = stream_data["frames"]
        audio_wav = stream_data["audio_wav"]

    if not frames and not audio_wav:
        raise RuntimeError("No frames or audio could be extracted from the target media stream.")

    # Dispatch to selected VLM
    if args.model == "claude":
        client = ClaudeClient()
        result = client.analyze_media(
            frames=frames,
            context_text=post_text,
            prompt=args.prompt,
        )
    else:
        client = GeminiClient()
        result = client.analyze_media(
            frames=frames,
            audio_wav=audio_wav,
            context_text=post_text,
            prompt=args.prompt,
        )

    return {
        "url": url,
        "mode": mode,
        "frames_extracted": len(frames),
        "has_audio": audio_wav is not None,
        "analysis": result["text"],
        "usage": result.get("usage", {}),
        "model": result.get("model"),
    }


def main():
    args = parse_args()
    try:
        data = asyncio.run(run_pipeline(args))
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print(f"\n=== Analysis for {data['url']} (Mode: {data['mode']}, Frames: {data['frames_extracted']}) ===\n")
            print(data["analysis"])
            if data.get("usage"):
                print(f"\n[Token Usage: {data['usage']}]")
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        if "CDP" in str(e) or "port" in str(e):
            sys.stderr.write("Tip: Ensure Chrome is launched with remote debugging enabled:\n")
            sys.stderr.write("     google-chrome --remote-debugging-port=9222 (or use BrowserOS Neo)\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
