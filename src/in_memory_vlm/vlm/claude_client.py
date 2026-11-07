"""Claude 3.7 Sonnet direct in-memory multimodal client."""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple, Union


class ClaudeClient:
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-7-sonnet-20250219"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model

    def analyze_media(
        self,
        frames: List[Union[bytes, str, Tuple[int, bytes]]],
        context_text: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Submits in-memory frames and context to Claude API via Base64 content blocks.
        """
        if not self.api_key:
            raise RuntimeError(
                "Anthropic API key is not configured. Set ANTHROPIC_API_KEY environment variable."
            )

        content_blocks = []
        user_prompt = prompt or "Analyze this video clip and extract all key insights, tools, and steps."
        content_blocks.append({"type": "text", "text": user_prompt})

        if context_text:
            content_blocks.append({"type": "text", "text": f"Surrounding Post Text:\n{context_text}"})

        for idx, item in enumerate(frames):
            b64_str: str
            if isinstance(item, tuple):
                _, frame_bytes = item
                b64_str = base64.b64encode(frame_bytes).decode("utf-8")
            elif isinstance(item, bytes):
                b64_str = base64.b64encode(item).decode("utf-8")
            else:
                b64_str = item

            content_blocks.append({"type": "text", "text": f"--- Keyframe #{idx + 1} ---"})
            content_blocks.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": b64_str,
                }
            })

        payload = {
            "model": self.model,
            "max_tokens": 2048,
            "messages": [{
                "role": "user",
                "content": content_blocks
            }]
        }

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=60.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Anthropic API error (HTTP {err.code}): {err_body}") from err

        text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")

        return {
            "text": text,
            "usage": data.get("usage", {}),
            "model": self.model,
        }
