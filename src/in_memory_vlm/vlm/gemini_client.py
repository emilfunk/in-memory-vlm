"""Gemini 2.5 Flash direct in-memory multimodal client."""

from __future__ import annotations

import base64
import os
from typing import Any, Dict, List, Optional, Tuple, Union
from google import genai
from google.genai import types


class GeminiClient:
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model = model
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

    def analyze_media(
        self,
        frames: List[Union[bytes, str, Tuple[int, bytes]]],
        audio_wav: Optional[bytes] = None,
        context_text: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Submits in-memory frames and audio directly to Gemini without saving to disk.
        """
        if not self.client:
            raise RuntimeError(
                "Gemini API key is not configured. Set GEMINI_API_KEY environment variable."
            )

        system_instruction = (
            "You are an expert video and visual analyst. You are provided with sequentially "
            "sampled keyframes and/or audio from an online media post. Analyze the content thoroughly: "
            "provide a concise summary, identify any code, tools, libraries, or physical techniques "
            "demonstrated, transcribe on-screen text, and provide bulleted actionable takeaways."
        )

        user_prompt = prompt or "Analyze this video clip and extract all key insights, tools, and steps."
        contents = [user_prompt]

        if context_text:
            contents.append(f"Surrounding Post Text:\n{context_text}")

        # Add in-memory audio if present
        if audio_wav:
            contents.append("Accompanying Audio Track:")
            contents.append(types.Part.from_bytes(data=audio_wav, mime_type="audio/wav"))

        # Add in-memory keyframes
        for idx, item in enumerate(frames):
            frame_bytes: bytes
            if isinstance(item, tuple):
                _, frame_bytes = item
            elif isinstance(item, str):
                frame_bytes = base64.b64decode(item)
            else:
                frame_bytes = item

            contents.append(f"Frame #{idx + 1}")
            contents.append(types.Part.from_bytes(data=frame_bytes, mime_type="image/jpeg"))

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.2,
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )

        usage = {}
        if getattr(response, "usage_metadata", None):
            usage = {
                "prompt_token_count": response.usage_metadata.prompt_token_count,
                "candidates_token_count": response.usage_metadata.candidates_token_count,
                "total_token_count": response.usage_metadata.total_token_count,
            }

        text = getattr(response, "text", None) or ""

        return {
            "text": text,
            "usage": usage,
            "model": self.model,
        }
