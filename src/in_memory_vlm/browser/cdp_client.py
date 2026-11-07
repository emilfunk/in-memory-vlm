"""Chrome DevTools Protocol (CDP) client for in-browser video frame extraction."""

from __future__ import annotations

import asyncio
import json
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional
import websockets


class CDPError(Exception):
    """Raised when communication with the CDP browser fails."""
    pass


def get_dom_extractor_script() -> str:
    """Loads the bundled in-page DOM extractor JavaScript snippet."""
    script_path = Path(__file__).parent / "dom_extractor.js"
    return script_path.read_text(encoding="utf-8")


async def extract_from_browser_tab(
    cdp_port: int = 9222,
    target_url: Optional[str] = None,
    num_frames: int = 12,
) -> Dict[str, Any]:
    """
    Connects to a running browser instance via CDP on cdp_port.
    Evaluates the in-memory frame extraction script on the target tab.
    """
    targets_endpoint = f"http://127.0.0.1:{cdp_port}/json"
    try:
        def _fetch_targets():
            req = urllib.request.Request(targets_endpoint)
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                return json.loads(resp.read().decode("utf-8"))

        targets: List[Dict[str, Any]] = await asyncio.to_thread(_fetch_targets)
    except Exception as e:
        raise CDPError(f"Could not connect to browser CDP on port {cdp_port}: {e}")

    # Find candidate page tab
    page_target = None
    if target_url:
        for t in targets:
            if t.get("type") == "page" and target_url in t.get("url", ""):
                page_target = t
                break

    if not page_target:
        # Fallback to the first available page target
        for t in targets:
            if t.get("type") == "page":
                page_target = t
                break

    if not page_target or not page_target.get("webSocketDebuggerUrl"):
        raise CDPError("No valid debuggable page tab found in the browser.")

    ws_url = page_target["webSocketDebuggerUrl"]
    script = get_dom_extractor_script()

    # Wrap or adjust call parameter for desired number of frames
    if num_frames != 12:
        script = script.replace("})(12);", f"}}({num_frames});")

    async with websockets.connect(ws_url, max_size=50 * 1024 * 1024) as ws:
        # 1. Optionally navigate if target_url provided and not already on it
        if target_url and target_url not in page_target.get("url", ""):
            nav_req = {
                "id": 1,
                "method": "Page.navigate",
                "params": {"url": target_url}
            }
            await ws.send(json.dumps(nav_req))
            await ws.recv()
            # Await page load
            await asyncio.sleep(3.0)

        # 2. Evaluate in-memory frame extractor script
        eval_req = {
            "id": 2,
            "method": "Runtime.evaluate",
            "params": {
                "expression": script,
                "awaitPromise": True,
                "returnByValue": True,
            }
        }
        await ws.send(json.dumps(eval_req))

        response_raw = await ws.recv()
        res = json.loads(response_raw)

        if "error" in res:
            raise CDPError(f"CDP evaluation error: {res['error']}")

        result_value = res.get("result", {}).get("result", {}).get("value", {})
        if not result_value.get("success", False):
            raise CDPError(result_value.get("error", "DOM extraction failed in browser."))

        return result_value
