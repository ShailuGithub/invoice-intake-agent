"""Language-model extractor. The model client is injected, so tests use a fake and no key is needed.

`make_default_client()` builds a real client from the environment (the API key is never stored in the repo).
"""
import base64
import json
import os
import re
from typing import Optional, Protocol

from app.extract import FIELDS

SYSTEM_PROMPT = (
    "You extract structured data from Indian GST invoices. Reply with ONLY a JSON object with exactly "
    "these keys: " + ", ".join(FIELDS) + ". Dates are yyyy-MM-dd. Amounts are plain numbers. "
    "Use null for anything not present. Do not guess amounts."
)


class ModelClient(Protocol):
    def complete(self, system: str, user_text: str, image_png: Optional[bytes] = None) -> str: ...


class LlmExtractor:
    def __init__(self, client: ModelClient):
        self.client = client

    def extract(self, text: Optional[str] = None, image_png: Optional[bytes] = None,
                feedback: Optional[list] = None) -> dict:
        if not text and not image_png:
            raise ValueError("need text or an image")
        prompt = text or "Extract the fields from the attached invoice image."
        if feedback:
            prompt += ("\n\nYour previous answer failed validation with these problems:\n- "
                       + "\n- ".join(feedback) + "\nRe-read the invoice and correct them.")
        raw = self.client.complete(SYSTEM_PROMPT, prompt, image_png)
        return self._parse(raw)

    @staticmethod
    def _parse(raw: str) -> dict:
        match = re.search(r"\{.*\}", raw, re.S)  # tolerate code fences or stray prose around the JSON
        if not match:
            raise ValueError("model reply contained no JSON object")
        data = json.loads(match.group(0))
        return {k: data.get(k) for k in FIELDS}


class AnthropicClient:
    """Adapter for the Anthropic Messages API. Reads ANTHROPIC_API_KEY from the environment."""

    def __init__(self, model: Optional[str] = None):
        import anthropic  # imported lazily so the package is optional for rules-only use
        self._client = anthropic.Anthropic()
        self._model = model or os.environ.get("INTAKE_MODEL", "claude-sonnet-5-5")

    def complete(self, system: str, user_text: str, image_png: Optional[bytes] = None) -> str:
        content = []
        if image_png:
            content.append({"type": "image", "source": {
                "type": "base64", "media_type": "image/png",
                "data": base64.b64encode(image_png).decode()}})
        content.append({"type": "text", "text": user_text})
        reply = self._client.messages.create(
            model=self._model, max_tokens=600, system=system,
            messages=[{"role": "user", "content": content}])
        return "".join(block.text for block in reply.content if block.type == "text")


def make_default_client() -> ModelClient:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("set ANTHROPIC_API_KEY to use the LLM extractor (or use INTAKE_EXTRACTOR=rules)")
    return AnthropicClient()
