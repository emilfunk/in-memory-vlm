"""In-memory stream piping orchestrator linking yt-dlp and ffmpeg."""

from __future__ import annotations

import asyncio
import os
import shutil
from typing import Dict, List, Optional, Tuple

from in_memory_vlm.core.frame_extractor import filter_keyframes, parse_mjpeg_stream


class StreamPipeError(Exception):
    """Raised when an in-memory streaming subprocess pipeline fails."""
    pass


async def extract_media_in_memory(
    url: str,
    cookies_browser: Optional[str] = None,
    cookies_file: Optional[str] = None,
    max_frames: int = 20,
    fps_sample: float = 0.5,
    include_audio: bool = True,
) -> Dict[str, any]:
    """
    Streams media from yt-dlp directly through ffmpeg pipes in RAM.
    Zero bytes are written to physical storage.

    Returns:
        Dict containing:
            - frames: List of (index, jpeg_bytes)
            - audio_wav: Optional[bytes]
            - frame_count: int
    """
    if not shutil.which("yt-dlp"):
        raise StreamPipeError("yt-dlp binary not found on system PATH.")
    if not shutil.which("ffmpeg"):
        raise StreamPipeError("ffmpeg binary not found on system PATH.")

    # 1. Build yt-dlp command targeting standard output stream (-o -)
    ytdlp_cmd = [
        "yt-dlp",
        "--no-warnings",
        "--no-cache-dir",
        "-f", "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "-o", "-",
    ]

    if cookies_browser:
        ytdlp_cmd.extend(["--cookies-from-browser", cookies_browser])
    elif cookies_file:
        ytdlp_cmd.extend(["--cookies", cookies_file])

    ytdlp_cmd.append(url)

    # 2. Build ffmpeg command reading pipe:0 and emitting MJPEG stream to pipe:1
    # We sample at fps_sample (e.g. 1 frame every 2 seconds: fps=0.5)
    ffmpeg_frames_cmd = [
        "ffmpeg",
        "-loglevel", "error",
        "-i", "pipe:0",
        "-vf", f"fps={fps_sample},scale='min(720,iw)':-2",
        "-f", "image2pipe",
        "-vcodec", "mjpeg",
        "pipe:1",
    ]

    # Spawn connected pipeline via OS pipe: yt-dlp -> ffmpeg
    r, w = os.pipe()
    try:
        p_ytdlp = await asyncio.create_subprocess_exec(
            *ytdlp_cmd,
            stdout=w,
            stderr=asyncio.subprocess.PIPE,
        )
        os.close(w)
        p_ffmpeg = await asyncio.create_subprocess_exec(
            *ffmpeg_frames_cmd,
            stdin=r,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        os.close(r)
    except Exception as e:
        try:
            os.close(w)
        except OSError:
            pass
        try:
            os.close(r)
        except OSError:
            pass
        raise StreamPipeError(f"Failed to spawn stream pipeline: {e}")

    # Read the MJPEG byte stream directly from memory
    raw_mjpeg, ffmpeg_err = await p_ffmpeg.communicate()
    _, ytdlp_err = await p_ytdlp.communicate()
    await p_ytdlp.wait()

    if p_ffmpeg.returncode != 0 and not raw_mjpeg:
        err_msg = (ffmpeg_err or ytdlp_err or b"Unknown pipeline error").decode("utf-8", errors="replace")
        raise StreamPipeError(f"Pipeline exited with error code {p_ffmpeg.returncode}: {err_msg.strip()}")

    # 3. Parse and filter frames in memory
    raw_frames = parse_mjpeg_stream(raw_mjpeg)
    selected_frames = filter_keyframes(raw_frames, max_frames=max_frames)

    # Optional: extract audio stream if requested
    audio_wav = None
    if include_audio:
        try:
            # We can run an audio-only stream pipe from yt-dlp
            audio_ytdlp_cmd = [
                "yt-dlp",
                "--no-warnings",
                "--no-cache-dir",
                "-f", "bestaudio/best",
                "-o", "-",
            ]
            if cookies_browser:
                audio_ytdlp_cmd.extend(["--cookies-from-browser", cookies_browser])
            elif cookies_file:
                audio_ytdlp_cmd.extend(["--cookies", cookies_file])
            audio_ytdlp_cmd.append(url)

            audio_ffmpeg_cmd = [
                "ffmpeg",
                "-loglevel", "error",
                "-i", "pipe:0",
                "-vn",
                "-ar", "16000",
                "-ac", "1",
                "-f", "wav",
                "pipe:1"
            ]

            ar, aw = os.pipe()
            p_aytdlp = await asyncio.create_subprocess_exec(
                *audio_ytdlp_cmd,
                stdout=aw,
                stderr=asyncio.subprocess.PIPE,
            )
            os.close(aw)
            p_affmpeg = await asyncio.create_subprocess_exec(
                *audio_ffmpeg_cmd,
                stdin=ar,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            os.close(ar)
            audio_wav, _ = await p_affmpeg.communicate()
            await p_aytdlp.communicate()
            await p_aytdlp.wait()
        except Exception:
            try:
                os.close(aw)
            except (OSError, UnboundLocalError):
                pass
            try:
                os.close(ar)
            except (OSError, UnboundLocalError):
                pass
            audio_wav = None

    return {
        "frames": selected_frames,
        "audio_wav": audio_wav,
        "frame_count": len(selected_frames),
        "raw_frame_count": len(raw_frames),
    }
