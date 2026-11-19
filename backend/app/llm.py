"""Optional LLM providers. WebSentinel-AI works fully offline without them (heuristic engine)."""

import json
from typing import Protocol

import httpx

from .config import get_settings


class LLMClient(Protocol):
    name: str

    async def complete_json(self, system: str, prompt: str) -> dict: ...


class OllamaClient:
    def __init__(self, url: str, model: str) -> None:
        self.url = url.rstrip("/")
        self.model = model
        self.name = f"ollama:{model}"

    async def complete_json(self, system: str, prompt: str) -> dict:
        async with httpx.AsyncClient(timeout=240) as client:
            resp = await client.post(
                f"{self.url}/api/chat",
                json={
                    "model": self.model,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.2, "num_predict": 2000},
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            resp.raise_for_status()
            return json.loads(resp.json()["message"]["content"])


class OpenAIClient:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model
        self.name = f"openai:{model}"

    async def complete_json(self, system: str, prompt: str) -> dict:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            resp.raise_for_status()
            return json.loads(resp.json()["choices"][0]["message"]["content"])


async def ollama_has_model(url: str, model: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            resp = await client.get(f"{url.rstrip('/')}/api/tags")
            resp.raise_for_status()
    except (httpx.HTTPError, ValueError):
        return False
    names = {m.get("name", "") for m in resp.json().get("models", [])}
    return model in names or f"{model}:latest" in names


async def get_llm() -> LLMClient | None:
    s = get_settings()
    if s.llm_provider == "none":
        return None
    if s.llm_provider in ("auto", "ollama") and await ollama_has_model(s.ollama_url, s.ollama_model):
        return OllamaClient(s.ollama_url, s.ollama_model)
    if s.llm_provider in ("auto", "openai") and s.openai_api_key:
        return OpenAIClient(s.openai_api_key, s.openai_model)
    return None
