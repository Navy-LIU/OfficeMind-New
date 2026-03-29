"""
ScreenReader — VLM-powered Screen Understanding
Uses Qwen-VL-Chat (local DGX Spark) to semantically interpret screenshots.
Supports:
  - Element location (buttons, inputs, tables)
  - Text extraction (OCR-free, layout-aware)
  - Action suggestion ("click X", "fill Y with Z")
  - Diff analysis between two screenshots
"""

from __future__ import annotations

import base64
import io
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from PIL import Image, ImageGrab

from .phash_filter import PHashFilter

logger = logging.getLogger(__name__)


@dataclass
class ScreenAnalysis:
    """Structured result from VLM screen analysis."""
    raw_response: str
    elements: List[Dict[str, Any]] = field(default_factory=list)
    suggested_action: Optional[str] = None
    confidence: float = 1.0
    latency_ms: float = 0.0
    skipped_vlm: bool = False   # True if pHash filter determined no change


def _image_to_base64(img: Image.Image, fmt: str = "PNG") -> str:
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode()


class ScreenReader:
    """
    Dual-layer screen reader:
      1. pHash filter — skip VLM if screen hasn't changed
      2. Qwen-VL-Chat — deep semantic understanding

    Parameters
    ----------
    vlm_base_url : str
        OpenAI-compatible API base URL (e.g. http://localhost:8000/v1)
    model_name : str
        Model identifier served by vLLM
    phash_threshold : int
        Hamming distance threshold for change detection
    screenshot_dir : str
        Directory to save screenshots for audit trail
    """

    SYSTEM_PROMPT = (
        "You are OfficeMind's screen analysis engine. "
        "When given a screenshot, identify all interactive UI elements "
        "(buttons, input fields, dropdowns, tables, links), extract visible text, "
        "and suggest the most appropriate next action to complete the user's task. "
        "Respond in structured JSON with keys: elements, text_content, suggested_action, confidence."
    )

    def __init__(
        self,
        vlm_base_url: str = "http://localhost:8000/v1",
        model_name: str = "Qwen-VL-Chat",
        phash_threshold: int = 10,
        screenshot_dir: str = "/tmp/officemind_screenshots",
        api_key: str = "EMPTY",
    ) -> None:
        self.vlm_base_url = vlm_base_url.rstrip("/")
        self.model_name = model_name
        self.api_key = api_key
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self._phash = PHashFilter(threshold=phash_threshold)
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    # ── Public API ────────────────────────────────────────────────────────────

    def capture_and_analyze(
        self,
        task_hint: str = "",
        save_screenshot: bool = True,
    ) -> ScreenAnalysis:
        """
        Capture current screen and analyze with VLM.
        Skips VLM call if pHash filter detects no meaningful change.
        """
        img = self._capture_screen()

        if save_screenshot:
            ts = int(time.time() * 1000)
            img.save(self.screenshot_dir / f"screen_{ts}.png")

        if not self._phash.has_changed(img):
            return ScreenAnalysis(
                raw_response="[pHash: screen unchanged, VLM skipped]",
                skipped_vlm=True,
            )

        return self._analyze_image(img, task_hint)

    def analyze_image_file(self, path: str, task_hint: str = "") -> ScreenAnalysis:
        """Analyze a saved screenshot file."""
        img = Image.open(path)
        return self._analyze_image(img, task_hint)

    def diff_screens(
        self,
        before: Image.Image,
        after: Image.Image,
        task_hint: str = "",
    ) -> ScreenAnalysis:
        """
        Ask VLM to compare two screenshots and describe what changed.
        Useful for verifying that an automated action had the expected effect.
        """
        prompt = (
            f"Compare these two screenshots (before and after an automated action). "
            f"Task context: {task_hint}. "
            f"Describe: 1) What changed, 2) Whether the action succeeded, "
            f"3) What to do next. Respond in JSON."
        )
        # Compose side-by-side image
        combined = Image.new("RGB", (before.width + after.width, max(before.height, after.height)))
        combined.paste(before, (0, 0))
        combined.paste(after, (before.width, 0))
        return self._analyze_image(combined, prompt)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _capture_screen(self) -> Image.Image:
        """Capture full screen. Falls back to blank image in headless env."""
        try:
            return ImageGrab.grab()
        except Exception:
            logger.warning("Screen capture unavailable (headless?), using blank image")
            return Image.new("RGB", (1920, 1080), color=(240, 240, 240))

    def _analyze_image(self, img: Image.Image, task_hint: str) -> ScreenAnalysis:
        """Send image + prompt to Qwen-VL-Chat via OpenAI-compatible API."""
        b64 = _image_to_base64(img)
        user_content = [
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"},
            },
            {
                "type": "text",
                "text": (
                    f"Analyze this screenshot for office automation. "
                    f"Current task: {task_hint or 'general analysis'}. "
                    f"Return JSON with: elements (list of {{type, label, bbox, actionable}}), "
                    f"text_content (str), suggested_action (str), confidence (0-1)."
                ),
            },
        ]

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.05,
            "max_tokens": 1024,
        }

        t0 = time.perf_counter()
        try:
            resp = self._session.post(
                f"{self.vlm_base_url}/chat/completions",
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.error("VLM call failed: %s", exc)
            raw = f"[VLM ERROR: {exc}]"

        latency = (time.perf_counter() - t0) * 1000

        # Try to parse structured JSON from response
        import json, re
        analysis = ScreenAnalysis(raw_response=raw, latency_ms=latency)
        try:
            # Extract JSON block from markdown code fences if present
            m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
            data = json.loads(m.group(1) if m else raw)
            analysis.elements = data.get("elements", [])
            analysis.suggested_action = data.get("suggested_action")
            analysis.confidence = float(data.get("confidence", 1.0))
        except Exception:
            pass  # raw_response still available

        logger.info(
            "VLM analysis: %d elements, action=%s, conf=%.2f, latency=%.0fms",
            len(analysis.elements),
            analysis.suggested_action,
            analysis.confidence,
            latency,
        )
        return analysis

    @property
    def phash_skip_rate(self) -> float:
        return self._phash.skip_rate
