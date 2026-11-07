# in-memory-vlm

A high-performance, zero-disk media stream interception and Vision-Language Model (VLM) ingestion engine.

Instead of downloading heavy MP4 video files to disk, `in-memory-vlm` intercepts media streams (HLS/DASH/MP4 chunks) or active browser `<video>` elements directly in RAM, extracts scene-aware keyframes and audio buffers in volatile memory, dispatches multimodal payloads directly to frontier VLMs (Gemini 2.5 Flash, Claude 3.7 Sonnet), and instantly discards all memory buffers.

## Core Features

- **Strict Zero-Disk Guarantee**: No `.mp4`, `.ts`, or `.jpg` temporary files ever touch physical storage (`/tmp`, Google Drive, or workspace). Everything is processed in RAM buffers (`BytesIO`, `Uint8Array`) and freed immediately after API dispatch.
- **Two Ingestion Modalities**:
  1. **Headless Stream Pipe**: Streams directly from `yt-dlp` through standard Unix pipes into an in-memory `ffmpeg` demuxer and scene-change filter.
  2. **Browser DOM Canvas Extractor**: Connects via Chrome DevTools Protocol (CDP) or browser automation (BrowserOS Neo / Agent-Reach profile) to fast-seek through playing video elements and extract Base64 JPEG frames via `OffscreenCanvas`.
- **Authenticated Session Support**: Leverages logged-in browser profiles (Chrome, Brave, Agent Reach) to access authenticated and walled platforms:
  - **YouTube**: Bypasses bot verification, age restrictions, and member gates via browser cookies.
  - **Instagram**: Intercepts authenticated Reels and stories in the live browser context.
  - **LinkedIn**: Captures video posts, keynote shares, and company video updates within active user sessions.
  - **X (Twitter)**: Streams video clips without hitting the paywalled Twitter API.
- **Scene-Aware Deduplication**: Heuristic color histogram entropy filters out duplicate or redundant frames, yielding 10–25 representative keyframes per clip instead of thousands of wasteful uniform frames.
- **Native VLM Ingestion**:
  - Direct byte dispatch to **Gemini 2.5 Flash** (`types.Part.from_bytes`) for simultaneous vision and audio reasoning.
  - Structured Base64 message payloads for **Claude 3.7 Sonnet** with timestamp markers.

## Architecture

```
[ Walled / Gated Video URL ]
             │
             ├── Mode 1: Live Browser (Instagram / LinkedIn)
             │     └── CDP (Port 9222) / BrowserOS Neo
             │           └── OffscreenCanvas fast-seek in DOM
             │                 └── Base64 JPEG frames in RAM
             │
             └── Mode 2: Headless Pipe (YouTube / X)
                   └── yt-dlp --cookies-from-browser (stdout)
                         └── ffmpeg pipe:0 -> pipe:1 (scene detect)
                               └── In-memory JPEG frames + WAV audio
                                     │
                                     ▼
                    [ Multimodal VLM Payload (RAM) ]
                                     │
                                     ▼
                      Gemini 2.5 Flash / Claude 3.7
                                     │
                                     ▼
                    [ buffer = null; gc.collect() ]
                             (Zero Disk)
```

## Quick Start

### Installation

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### CLI Usage

```bash
# Watch a YouTube video in memory using Gemini Flash
vlm-watch "https://www.youtube.com/watch?v=..." --cookies chrome --model gemini

# Watch an Instagram Reel via active browser CDP tab
vlm-watch "https://www.instagram.com/reel/..." --browser-cdp 9222

# Watch an X post clip and format as JSON
vlm-watch "https://x.com/.../status/..." --json
```

## Testing

```bash
pytest
```
