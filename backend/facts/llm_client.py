import json
import time
import urllib.request
import urllib.error
from typing import Type, TypeVar
from pydantic import BaseModel
from google import genai
from google.genai import types

from core.config import settings

T = TypeVar("T", bound=BaseModel)

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"


def get_gemini_client(api_key: str | None = None):
    return genai.Client(api_key=api_key or settings.gemini_api_key)


GROQ_DEFAULT_MODELS = [
    "llama-3.1-8b-instant",
    "llama-3.2-3b-preview",
    "llama-3.2-1b-preview",
    "llama-3.2-11b-vision-preview",
    "llama3-8b-8192",
    "llama-3.3-70b-versatile",
    "llama3-70b-8192",
    "gemma2-9b-it",
    "deepseek-r1-distill-llama-70b",
    "deepseek-r1-distill-qwen-32b",
    "qwen-2.5-32b",
    "qwen-2.5-coder-32b",
]


def fetch_groq_models(api_key: str | None = None) -> list[str]:
    """Fetch live available model identifiers from Groq API for the given key."""
    key = api_key or settings.groq_api_key
    if not key:
        return GROQ_DEFAULT_MODELS

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/models",
        headers={
            "Authorization": f"Bearer {key}",
            "User-Agent": "FactKnowledgeLayer/1.0",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            live_models = [m["id"] for m in data.get("data", []) if m.get("active", True)]
            return live_models if live_models else GROQ_DEFAULT_MODELS
    except Exception as exc:
        print(f"[Groq Client] Could not fetch live models ({exc}), using default catalog.")
        return GROQ_DEFAULT_MODELS


def call_groq(
    prompt: str,
    system_instruction: str,
    response_schema: Type[T],
    model: str | None = None,
    api_key: str | None = None,
    max_retries: int = 3,
) -> T:
    """
    Call Groq API using OpenAI-compatible JSON mode.
    Uses urllib.request (zero third-party dependencies).
    """
    key = api_key or settings.groq_api_key
    if not key:
        raise ValueError(
            "Groq API key is not configured. Please set GROQ_API_KEY in your .env or the UI Settings."
        )

    groq_model = model or settings.groq_model or "llama-3.1-8b-instant"
    schema_desc = json.dumps(response_schema.model_json_schema(), indent=2)

    enhanced_system = (
        f"{system_instruction}\n\n"
        "CRITICAL: You must return a valid JSON object matching the schema below. "
        "Do not include any Markdown fences (like ```json), commentary, or notes. "
        f"JSON Schema:\n{schema_desc}"
    )

    payload = {
        "model": groq_model,
        "messages": [
            {"role": "system", "content": enhanced_system},
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1,
    }

    req_data = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "FactKnowledgeLayer/1.0",
    }

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                GROQ_ENDPOINT, data=req_data, headers=headers, method="POST"
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                resp_json = json.loads(resp.read().decode("utf-8"))
                content = resp_json["choices"][0]["message"]["content"]
                return response_schema.model_validate_json(content)

        except urllib.error.HTTPError as http_err:
            raw_err = http_err.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw_err)
                msg = parsed.get("error", {}).get("message", raw_err)
            except Exception:
                msg = raw_err

            err_detail = f"Groq Error (HTTP {http_err.code}): {msg}"
            # Fail immediately on permanent client errors (model not found, invalid key, bad payload)
            if http_err.code in (400, 401, 403, 404):
                raise RuntimeError(err_detail)

            if attempt == max_retries - 1:
                raise RuntimeError(f"Groq API request failed: {err_detail}")
            delay = 2 ** attempt
            print(f"[Groq Client] Attempt {attempt + 1} failed ({err_detail}). Retrying in {delay}s...")
            time.sleep(delay)

        except Exception as exc:
            if attempt == max_retries - 1:
                raise RuntimeError(f"Groq API request failed: {exc}")
            delay = 2 ** attempt
            print(f"[Groq Client] Attempt {attempt + 1} failed ({exc}). Retrying in {delay}s...")
            time.sleep(delay)

    raise RuntimeError("Unreachable")


def call_gemini(
    prompt: str,
    system_instruction: str,
    response_schema: Type[T],
    model: str | None = None,
    api_key: str | None = None,
    max_retries: int = 3,
) -> T:
    """
    Call Google Gemini using the official google-genai SDK.
    """
    client = get_gemini_client(api_key)
    target_model = model or settings.gemini_model or "gemini-3.5-flash"
    # Graceful model alias normalization
    model_aliases = {
        "gemini-3.6-lite": "gemini-3.5-flash-lite",
        "gemini-3.6-flash-lite": "gemini-3.5-flash-lite",
        "gemini-3.5-lite": "gemini-3.5-flash-lite",
        "gemini-3-flash": "gemini-3.5-flash",
    }
    target_model = model_aliases.get(target_model, target_model)

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=target_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                ),
            )
            return response_schema.model_validate_json(response.text)

        except Exception as exc:
            error_str = str(exc)
            # Check for rate limit / quota exceeded (429 or RESOURCE_EXHAUSTED)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                if settings.groq_api_key:
                    print(
                        f"\n⚠️ [Circuit Breaker] Gemini rate limit hit ({exc})! "
                        f"Auto-failing over to Groq ({settings.groq_model})..."
                    )
                    return call_groq(prompt, system_instruction, response_schema, model=settings.groq_model)
                else:
                    raise RuntimeError(f"Gemini API Quota Exceeded (429 Rate Limit): {exc}")

            if attempt == max_retries - 1:
                raise

            delay = 2 ** attempt
            print(f"[Gemini Client] Attempt {attempt + 1} failed ({exc}). Retrying in {delay}s...")
            time.sleep(delay)

    raise RuntimeError("Unreachable")


def call_structured_llm(
    prompt: str,
    system_instruction: str,
    response_schema: Type[T],
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
) -> T:
    """
    Unified multi-provider entrypoint for structured LLM extraction and reasoning.
    Selects Gemini or Groq based on configuration or runtime arguments.
    """
    target_provider = (provider or settings.llm_provider or "gemini").lower()

    if target_provider == "groq":
        return call_groq(prompt, system_instruction, response_schema, model=model, api_key=api_key)
    else:
        return call_gemini(prompt, system_instruction, response_schema, model=model, api_key=api_key)
