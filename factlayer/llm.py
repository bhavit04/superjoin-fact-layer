"""One JSON-in/JSON-out interface over Gemini, Anthropic, OpenAI, and a replay cache.

Three things this layer is responsible for, all of which exist because of how the
pipeline uses it:

* **Provider independence.** Nothing above this file knows which vendor answered.
  The prompts are plain text and the contract is "return JSON", so switching
  providers is an environment variable.
* **A content-addressed disk cache.** The cache key is a hash of the prompt, not
  of the provider, so a cache built with one model replays under any
  configuration -- including with no API key at all. That is what lets this repo
  ship a runnable demo without shipping a credential.
* **Surviving free-tier rate limits.** Retries with backoff, honouring
  ``Retry-After``, and a bounded concurrency semaphore.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from .config import Settings, get_settings

# Bumped when a prompt's meaning changes, to invalidate cache entries that were
# produced by an older version of a task.
PROMPT_VERSION = "v1"

_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)
_TRAILING_COMMA = re.compile(r",(\s*[}\]])")


class LLMError(RuntimeError):
    pass


class LLMUnavailable(LLMError):
    """No credential and no cache entry -- the caller must degrade gracefully."""


@dataclass
class Usage:
    calls: int = 0
    cache_hits: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    retries: int = 0
    errors: int = 0
    seconds: float = 0.0

    def merge(self, other: "Usage") -> None:
        for key in ("calls", "cache_hits", "input_tokens", "output_tokens", "retries", "errors"):
            setattr(self, key, getattr(self, key) + getattr(other, key))
        self.seconds += other.seconds

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def extract_json(text: str) -> Any:
    """Pull a JSON value out of a model response that may be wrapped in prose."""
    if text is None:
        raise LLMError("empty response")
    cleaned = _FENCE.sub("", text.strip())
    for attempt in (cleaned, _TRAILING_COMMA.sub(r"\1", cleaned)):
        try:
            return json.loads(attempt)
        except json.JSONDecodeError:
            pass
    # Fall back to the outermost balanced object or array in the text.
    for opener, closer in (("{", "}"), ("[", "]")):
        start, end = cleaned.find(opener), cleaned.rfind(closer)
        if start != -1 and end > start:
            candidate = cleaned[start : end + 1]
            for attempt in (candidate, _TRAILING_COMMA.sub(r"\1", candidate)):
                try:
                    return json.loads(attempt)
                except json.JSONDecodeError:
                    continue
    raise LLMError(f"could not parse JSON from response: {cleaned[:300]!r}")


class RateLimiter:
    """A token bucket that paces requests to a requests-per-minute budget.

    Free-tier quotas are per-minute, and the natural approach -- fire everything
    and retry on 429 -- is actively counterproductive against them: the rejected
    requests still count, so bursting turns a 20/min budget into far less than
    20/min of useful work. Pacing to just under the limit is both faster overall
    and kinder to the quota.
    """

    def __init__(self, per_minute: float):
        self.interval = 60.0 / max(per_minute, 0.1)
        self._lock = asyncio.Lock()
        self._next_slot = 0.0

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            wait = max(0.0, self._next_slot - now)
            self._next_slot = max(now, self._next_slot) + self.interval
        if wait:
            await asyncio.sleep(wait)

    async def pause_for(self, seconds: float) -> None:
        """Push every queued request back, after the server tells us to wait."""
        async with self._lock:
            self._next_slot = max(self._next_slot, time.monotonic() + seconds)


_RETRY_HINT = re.compile(r"retry in ([\d.]+)\s*s", re.IGNORECASE)


def parse_retry_hint(body: str) -> float | None:
    """Gemini puts its backoff advice in the error body, not in Retry-After."""
    match = _RETRY_HINT.search(body or "")
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


class DiskCache:
    """Content-addressed JSON cache, sharded so directories stay small."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def key(system: str, prompt: str, task: str) -> str:
        payload = f"{PROMPT_VERSION}\x00{task}\x00{system}\x00{prompt}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def path_for(self, key: str) -> Path:
        return self.root / key[:2] / f"{key}.json"

    def get(self, key: str) -> str | None:
        path = self.path_for(key)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))["response"]
        except Exception:
            return None

    def put(self, key: str, response: str, meta: dict[str, Any]) -> None:
        path = self.path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {"key": key, "response": response, "created_at": time.time(), **meta}
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(path)

    def size(self) -> int:
        return sum(1 for _ in self.root.rglob("*.json"))


class LLMClient:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.cache = DiskCache(self.settings.cache_dir)
        self.usage = Usage()
        self._semaphore = asyncio.Semaphore(max(1, self.settings.max_concurrency))
        self._limiter = RateLimiter(self.settings.requests_per_minute)
        self.failures: list[dict[str, str]] = []
        self._client: httpx.AsyncClient | None = None
        self._no_cache = os.getenv("FACTLAYER_NO_CACHE", "").lower() in {"1", "true", "yes"}
        # Which Gemini API this key can actually reach; resolved on first call.
        self._gemini_api: str | None = os.getenv("FACTLAYER_GEMINI_API") or None
        self._gemini_probed = False

    async def __aenter__(self) -> "LLMClient":
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=20.0))
        return self

    async def __aexit__(self, *exc) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def available(self) -> bool:
        return self.settings.has_live_llm

    def describe(self) -> dict[str, Any]:
        return {
            "provider": self.settings.provider,
            "model": self.settings.model,
            "live": self.available,
            "cache_entries": self.cache.size(),
            "usage": self.usage.to_dict(),
        }

    async def complete_json(
        self,
        system: str,
        prompt: str,
        task: str,
        *,
        max_output_tokens: int = 16384,
        temperature: float = 0.0,
        default: Any = None,
    ) -> Any:
        """Return parsed JSON for a prompt, from cache when possible.

        ``default`` is returned instead of raising when nothing can answer -- the
        pipeline treats a missing LLM as degraded, not fatal.
        """
        key = self.cache.key(system, prompt, task)
        if not self._no_cache:
            cached = self.cache.get(key)
            if cached is not None:
                self.usage.cache_hits += 1
                try:
                    return extract_json(cached)
                except LLMError:
                    pass  # A poisoned cache entry should not be fatal; re-fetch below.

        if not self.available:
            if default is not None:
                return default
            raise LLMUnavailable(
                f"No cached response for task '{task}' and no API key for provider "
                f"'{self.settings.provider}'. Set {self.settings.provider.upper()}_API_KEY, "
                f"or run with FACTLAYER_PROVIDER=replay against a populated cache."
            )

        async with self._semaphore:
            started = time.time()
            try:
                await self._limiter.acquire()
                text, usage = await self._call_with_retry(system, prompt, max_output_tokens, temperature)
            except Exception as exc:
                self.usage.errors += 1
                self.failures.append({"task": task, "error": f"{type(exc).__name__}: {exc}"[:300]})
                raise LLMError(f"{task}: {exc}") from exc
            finally:
                self.usage.seconds += time.time() - started

        self.usage.calls += 1
        self.usage.input_tokens += usage.get("input", 0)
        self.usage.output_tokens += usage.get("output", 0)
        self.cache.put(
            key, text,
            {"provider": self.settings.provider, "model": self.settings.model, "task": task, "usage": usage},
        )
        try:
            return extract_json(text)
        except LLMError as exc:
            self.usage.errors += 1
            self.failures.append({"task": task, "error": f"unparseable response: {exc}"[:300]})
            raise

    async def _call_with_retry(
        self, system: str, prompt: str, max_output_tokens: int, temperature: float
    ) -> tuple[str, dict[str, int]]:
        attempts = 6
        delay = 2.0
        last: Exception | None = None
        for attempt in range(attempts):
            try:
                return await self._call(system, prompt, max_output_tokens, temperature)
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status not in (408, 409, 429, 500, 502, 503, 504):
                    raise
                last = exc
                retry_after = exc.response.headers.get("retry-after")
                hinted = parse_retry_hint(exc.response.text)
                if retry_after and retry_after.isdigit():
                    wait = float(retry_after)
                elif hinted is not None:
                    wait = hinted
                else:
                    wait = delay
                wait += random.uniform(0, 1.5)  # jitter, so parallel workers don't resynchronize
                if status == 429:
                    # Hold every other in-flight request too: the budget is shared.
                    await self._limiter.pause_for(wait)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last = exc
                wait = delay + random.uniform(0, 1.0)
            self.usage.retries += 1
            if attempt == attempts - 1:
                break
            await asyncio.sleep(min(wait, 60.0))
            delay = min(delay * 2, 45.0)
        raise LLMError(f"request failed after {attempts} attempts: {last}")

    async def _call(
        self, system: str, prompt: str, max_output_tokens: int, temperature: float
    ) -> tuple[str, dict[str, int]]:
        if self._client is None:
            raise LLMError("LLMClient must be used as an async context manager")
        provider = self.settings.provider
        if provider == "gemini":
            return await self._call_gemini(system, prompt, max_output_tokens, temperature)
        if provider == "anthropic":
            return await self._call_anthropic(system, prompt, max_output_tokens, temperature)
        if provider == "openai":
            return await self._call_openai(system, prompt, max_output_tokens, temperature)
        raise LLMError(f"unknown provider {provider!r}")

    async def _call_gemini(self, system, prompt, max_output_tokens, temperature):
        """Google now serves two incompatible APIs and which one a key can reach
        depends on when the key was issued: newer keys get the Interactions API
        and are refused by ``generateContent`` with a 404 on every model, while
        older keys are the other way round. Rather than make the user work out
        which they have, the first call probes and the answer is reused."""
        if self._gemini_api is None:
            self._gemini_api = "interactions"
        try:
            if self._gemini_api == "interactions":
                return await self._call_gemini_interactions(system, prompt, max_output_tokens, temperature)
            return await self._call_gemini_generate(system, prompt, max_output_tokens, temperature)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 404 or self._gemini_probed:
                raise
            self._gemini_probed = True
            self._gemini_api = "generate" if self._gemini_api == "interactions" else "interactions"
            if self._gemini_api == "interactions":
                return await self._call_gemini_interactions(system, prompt, max_output_tokens, temperature)
            return await self._call_gemini_generate(system, prompt, max_output_tokens, temperature)

    async def _call_gemini_interactions(self, system, prompt, max_output_tokens, temperature):
        """The current API. Note there is no JSON response-mime setting here: the
        only structured-output control is a full JSON schema, and supplying a bare
        object type makes the model return an empty object. The prompts ask for
        JSON and ``extract_json`` cleans up whatever comes back."""
        resp = await self._client.post(
            "https://generativelanguage.googleapis.com/v1beta/interactions",
            params={"key": self.settings.api_key},
            json={
                "model": self.settings.model,
                "input": prompt,
                "system_instruction": system,
                "generation_config": {
                    "temperature": temperature,
                    "max_output_tokens": max_output_tokens,
                    # Extraction is transcription-shaped work; deep reasoning here
                    # burns tokens and latency without improving the output.
                    "thinking_level": "low",
                },
            },
        )
        resp.raise_for_status()
        data = resp.json()
        text = ""
        for step in data.get("steps", []):
            if step.get("type") == "model_output":
                text += "".join(
                    part.get("text", "") for part in step.get("content", [])
                    if part.get("type") == "text"
                )
        if not text:
            raise LLMError(f"gemini returned no model output: {json.dumps(data)[:300]}")
        usage = data.get("usage", {})
        return text, {
            "input": usage.get("total_input_tokens", 0),
            "output": usage.get("total_output_tokens", 0),
        }

    async def _call_gemini_generate(self, system, prompt, max_output_tokens, temperature):
        """The older generateContent API, kept for keys that only reach that one."""
        model = self.settings.model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": system}]},
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
                "responseMimeType": "application/json",
            },
        }
        resp = await self._client.post(url, params={"key": self.settings.api_key}, json=body)
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates") or []
        if not candidates:
            raise LLMError(f"gemini returned no candidates: {json.dumps(data)[:300]}")
        parts = candidates[0].get("content", {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts)
        meta = data.get("usageMetadata", {})
        return text, {
            "input": meta.get("promptTokenCount", 0),
            "output": meta.get("candidatesTokenCount", 0),
        }

    async def _call_anthropic(self, system, prompt, max_output_tokens, temperature):
        resp = await self._client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.settings.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.settings.model,
                "max_tokens": max_output_tokens,
                "temperature": temperature,
                "system": system,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        usage = data.get("usage", {})
        return text, {"input": usage.get("input_tokens", 0), "output": usage.get("output_tokens", 0)}

    async def _call_openai(self, system, prompt, max_output_tokens, temperature):
        resp = await self._client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.settings.api_key}"},
            json={
                "model": self.settings.model,
                "temperature": temperature,
                "max_tokens": max_output_tokens,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return text, {
            "input": usage.get("prompt_tokens", 0),
            "output": usage.get("completion_tokens", 0),
        }
