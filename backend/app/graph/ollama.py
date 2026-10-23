"""Local Ollama chat client. Stdlib HTTP only. No paid model API."""

from __future__ import annotations

import json
import urllib.error
import urllib.request


class OllamaError(Exception):
    """The local model did not return a usable reply."""


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout_s: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_s = timeout_s

    def complete(self, prompt: str) -> str:
        payload = {
            "model": self._model,
            "stream": False,
            "format": "json",
            "messages": [{"role": "user", "content": prompt}],
            "options": {"temperature": 0},
        }
        request = urllib.request.Request(
            f"{self._base_url}/api/chat",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_s) as response:
                body = json.loads(response.read().decode())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            raise OllamaError(str(exc)) from exc
        content = body.get("message", {}).get("content") if isinstance(body, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise OllamaError("empty model reply")
        return content

    def reachable(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self._base_url}/api/tags", timeout=0.4) as response:
                return response.status == 200
        except (urllib.error.URLError, TimeoutError, OSError):
            return False
