# Implementation & Verification Plan: in-memory-vlm

## Objective
Build a production-grade, zero-disk media interception and VLM reasoning engine that extracts frames and audio from authenticated platforms (YouTube, Instagram, LinkedIn, X) purely in memory and sends them directly to Gemini 2.5 Flash and Claude.

## Phase 1: Core Architecture & In-Memory Pipeline (Completed)
- [x] Create project layout and package configuration (`pyproject.toml`, `README.md`).
- [x] Implement in-memory Unix stream piping (`yt-dlp` $\to$ `ffmpeg` $\to$ RAM buffers).
- [x] Implement JPEG frame parsing from raw MJPEG byte streams without disk writes.
- [x] Implement scene-change detection & frame deduplication in memory.
- [x] Implement 16kHz mono audio extraction to RAM buffer.

## Phase 2: Browser & CDP Ingestion (Completed)
- [x] Create `dom_extractor.js` for zero-disk `OffscreenCanvas` frame extraction from HTML5 `<video>` tags.
- [x] Implement `cdp_client.py` for communicating with Chrome DevTools Protocol (port 9222 / Agent Reach browser / BrowserOS).
- [x] Capture surrounding post context (caption, author, comments) concurrently.

## Phase 3: VLM Dispatchers & CLI (Completed)
- [x] Implement `GeminiClient` utilizing `google-genai` SDK with inline bytes (`types.Part.from_bytes`).
- [x] Implement `ClaudeClient` utilizing Anthropic Base64 image and text blocks.
- [x] Implement unified CLI (`vlm-watch`) with flags for cookies, models, frame limits, and JSON output.

## Phase 4: Verification & Benchmarking
- [x] Unit test suite covering buffer extraction, stream slicing, and mock VLM dispatch.
- [x] Verification of zero-disk invariant (verifying `/tmp` and local directory during runs).
- [x] Reviewer subagent audit to evaluate implementation quality, safety, and operational readiness.
