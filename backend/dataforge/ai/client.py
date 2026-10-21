"""
DataForge AI - Google GenAI SDK Client Wrapper
Supports Structured Outputs, Tool Calling, and Streaming with Automatic Retries.
"""

import os
import logging
from typing import Optional, Any
from dotenv import load_dotenv

from dataforge.settings import ROOT_DIR

logger = logging.getLogger(__name__)

# Ensure environment variables are loaded
_env_path = ROOT_DIR / ".env" if (ROOT_DIR / ".env").exists() else ROOT_DIR.parent / ".env"
load_dotenv(override=True, dotenv_path=_env_path)
_backend_env = ROOT_DIR / "backend" / ".env"
if _backend_env.exists():
    load_dotenv(override=True, dotenv_path=_backend_env)

DEFAULT_PRIMARY_MODEL = os.getenv("GEMINI_MODEL", "gemini-4-argon")
FALLBACK_MODELS = ["gemini-4-argon", "gemini-2.5-flash", "gemini-flash-latest", "gemini-flash-lite-latest"]

_cached_client: Optional[Any] = None
_last_api_key: Optional[str] = None

def get_api_key() -> str:
    """Retrieve GEMINI_API_KEY from environment with hot reload."""
    if _env_path.exists():
        load_dotenv(override=True, dotenv_path=_env_path)
    return (os.getenv("GEMINI_API_KEY") or "").strip("'\"")

def is_available() -> bool:
    """Check if Gemini API Key is configured and ready."""
    return bool(get_api_key())

def get_genai_client():
    """Instantiate and cache Google GenAI SDK Client, invalidating cache when key changes."""
    global _cached_client, _last_api_key
    api_key = get_api_key()
    if not api_key:
        logger.warning("[dataforge.ai] GEMINI_API_KEY is not set.")
        _cached_client = None
        _last_api_key = None
        return None

    if _cached_client is not None and _last_api_key == api_key:
        return _cached_client

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        _cached_client = client
        _last_api_key = api_key
        logger.info("[dataforge.ai] Google GenAI SDK Client initialized with active key.")
        return _cached_client
    except Exception as exc:
        logger.error("[dataforge.ai] Failed to initialize Google GenAI SDK Client: %s", exc)
        _cached_client = None
        _last_api_key = None
        return None

def generate_structured(
    prompt: str,
    response_schema: Any,
    temperature: float = 0.1,
    system_instruction: Optional[str] = None,
    primary_model: str = DEFAULT_PRIMARY_MODEL,
    fallback_model: Optional[str] = None,
) -> Any:
    """
    Generate content with guaranteed schema compliance via Google GenAI Structured Outputs.
    Falls back gracefully if primary model experiences transient capacity limits.
    """
    client = get_genai_client()
    if not client:
        raise ValueError("GEMINI_API_KEY is not configured or client initialization failed.")

    from google.genai import types

    config = types.GenerateContentConfig(
        temperature=temperature,
        response_mime_type="application/json",
        response_schema=response_schema,
        system_instruction=system_instruction,
    )

    models_to_try = [primary_model] + [m for m in FALLBACK_MODELS if m != primary_model]
    last_error = None

    for model_name in models_to_try:
        try:
            logger.info("[dataforge.ai] Dispatching structured request to model: %s", model_name)
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            if hasattr(response, "parsed") and response.parsed is not None:
                return response.parsed
            
            # If parsed is not populated directly, load from text
            if hasattr(response, "text") and response.text:
                import json
                parsed_json = json.loads(response.text)
                if hasattr(response_schema, "model_validate"):
                    return response_schema.model_validate(parsed_json)
                return parsed_json
            
            raise RuntimeError(f"Model {model_name} returned empty text.")
        except Exception as exc:
            last_error = exc
            err_str = str(exc)
            logger.warning("[dataforge.ai] Model %s failed: %s.", model_name, exc)
            # 401 (invalid key) and 402 (prepayment credits depleted) are account-level errors.
            # Trying subsequent models under the same key will only add network latency.
            if "402" in err_str or "prepayment" in err_str.lower() or "401" in err_str:
                logger.warning("[dataforge.ai] Account billing or authentication limit reached (%s). Bypassing remaining fallback models.", err_str[:120])
                break
            continue

    raise RuntimeError(f"All Gemini models failed: {last_error}")

def generate_stream(
    prompt: str,
    temperature: float = 0.1,
    system_instruction: Optional[str] = None,
    model: str = DEFAULT_PRIMARY_MODEL,
):
    """
    Stream tokens from Gemini for real-time frontend chat rendering.
    """
    client = get_genai_client()
    if not client:
        raise ValueError("GEMINI_API_KEY is not configured.")

    from google.genai import types

    config = types.GenerateContentConfig(
        temperature=temperature,
        system_instruction=system_instruction,
    )

    return client.models.generate_content_stream(
        model=model,
        contents=prompt,
        config=config,
    )
