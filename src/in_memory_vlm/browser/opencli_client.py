"""OpenCLI Browser Bridge client for zero-setup in-browser frame extraction."""

from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional


class OpenCLIError(Exception):
    """Raised when communication with OpenCLI browser bridge fails."""
    pass


def get_dom_extractor_script() -> str:
    """Loads the bundled in-page DOM extractor JavaScript snippet."""
    script_path = Path(__file__).parent / "dom_extractor.js"
    return script_path.read_text(encoding="utf-8")


def is_opencli_available() -> bool:
    """Checks if opencli is installed and its daemon is active."""
    if not shutil.which("opencli"):
        return False
    try:
        res = subprocess.run(
            ["opencli", "doctor"],
            capture_output=True,
            text=True,
            timeout=3.0,
        )
        return res.returncode == 0
    except Exception:
        return False


async def extract_via_opencli(
    target_url: str,
    num_frames: int = 12,
    session_name: str = "vlm_stream",
    window_mode: str = "background",
) -> Dict[str, Any]:
    """
    Leverages OpenCLI's connected Chrome extension to open the target URL in a background
    tab, execute the in-memory DOM extractor script, and return keyframes without touching disk.
    """
    if not shutil.which("opencli"):
        raise OpenCLIError("opencli executable not found on system PATH.")

    # 1. Open URL in background tab
    open_cmd = [
        "opencli", "browser", session_name, "open", target_url,
        "--window", window_mode,
    ]
    p_open = await asyncio.create_subprocess_exec(
        *open_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await p_open.communicate()
    if p_open.returncode != 0:
        raise OpenCLIError(f"opencli failed to open URL: {stderr.decode(errors='replace')}")

    # Allow page and video tag to settle in DOM
    await asyncio.sleep(3.0)

    # 2. Evaluate in-memory frame extractor script
    script = get_dom_extractor_script()
    if num_frames != 12:
        script = script.replace("})(12);", f"}}({num_frames});")

    eval_cmd = [
        "opencli", "browser", session_name, "eval", script
    ]

    p_eval = await asyncio.create_subprocess_exec(
        *eval_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    eval_out, eval_err = await p_eval.communicate()

    # Always ensure the tab lease is closed
    close_cmd = ["opencli", "browser", session_name, "close"]
    p_close = await asyncio.create_subprocess_exec(*close_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    await p_close.communicate()

    if p_eval.returncode != 0:
        raise OpenCLIError(f"opencli eval error: {eval_err.decode(errors='replace')}")

    raw_output = eval_out.decode("utf-8", errors="replace").strip()
    
    # OpenCLI outputs stringified result or JSON; parse cleanly
    try:
        # Find json object in stdout
        json_start = raw_output.find("{")
        json_end = raw_output.rfind("}")
        if json_start != -1 and json_end != -1:
            data = json.loads(raw_output[json_start : json_end + 1])
            if not data.get("success", False):
                raise OpenCLIError(data.get("error", "DOM extraction failed."))
            return data
    except Exception as e:
        raise OpenCLIError(f"Failed to parse extractor response from opencli: {e}\nOutput: {raw_output}")

    raise OpenCLIError("No valid extraction payload returned from opencli.")
