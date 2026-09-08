import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.config import settings
from facts.llm_client import call_structured_llm, GROQ_DEFAULT_MODELS, fetch_groq_models

router = APIRouter(prefix="/settings", tags=["Settings"])


class ProviderInfo(BaseModel):
    id: str
    name: str
    active_model: str
    available_models: list[str]
    has_key: bool


class SettingsResponse(BaseModel):
    active_provider: str
    active_model: str
    circuit_breaker_enabled: bool = True
    providers: list[ProviderInfo]


class UpdateSettingsRequest(BaseModel):
    provider: str | None = Field(None, description="gemini | groq")
    model: str | None = Field(None, description="Model identifier")
    api_key: str | None = Field(None, description="Optional API key for the chosen provider")


class TestConnectionRequest(BaseModel):
    provider: str
    model: str
    api_key: str | None = None


class TestConnectionResponse(BaseModel):
    success: bool
    latency_ms: int | None = None
    message: str


class PingResult(BaseModel):
    status: str


@router.get("", response_model=SettingsResponse)
def get_settings():
    """Retrieve active LLM provider and available configurations."""
    active_prov = settings.llm_provider.lower()
    active_mod = settings.groq_model if active_prov == "groq" else settings.gemini_model

    providers = [
        ProviderInfo(
            id="gemini",
            name="Google Gemini",
            active_model=settings.gemini_model,
            available_models=[
                "gemini-3.5-flash",
                "gemini-3.5-flash-lite",
                "gemini-3.6-flash",
                "gemini-3.7-flash",
                "gemini-3.8-flash",
                "gemini-flash-latest",
                "gemini-flash-lite-latest",
                "gemini-pro-latest",
            ],
            has_key=bool(settings.gemini_api_key),
        ),
        ProviderInfo(
            id="groq",
            name="Groq (Ultra-Fast Inference)",
            active_model=settings.groq_model,
            available_models=GROQ_DEFAULT_MODELS,
            has_key=bool(settings.groq_api_key),
        ),
    ]

    return SettingsResponse(
        active_provider=active_prov,
        active_model=active_mod,
        circuit_breaker_enabled=bool(settings.groq_api_key),
        providers=providers,
    )


@router.get("/models")
def get_models_for_provider(provider: str = "groq", api_key: str | None = None):
    """
    Dynamically discover models supported by the provider, querying live API catalog if key is present.
    """
    if provider.lower() == "groq":
        live_models = fetch_groq_models(api_key)
        return {"provider": "groq", "models": live_models}
    elif provider.lower() == "gemini":
        return {
            "provider": "gemini",
            "models": [
                "gemini-3.5-flash",
                "gemini-3.5-flash-lite",
                "gemini-3.6-flash",
                "gemini-3.7-flash",
                "gemini-3.8-flash",
                "gemini-flash-latest",
                "gemini-flash-lite-latest",
                "gemini-pro-latest",
            ],
        }
    return {"provider": provider, "models": []}


@router.post("", response_model=SettingsResponse)
def update_settings(req: UpdateSettingsRequest):
    """
    Update active LLM provider, active model, or provide an API key at runtime.
    Changes take effect immediately without requiring a server restart.
    """
    if req.provider:
        prov = req.provider.lower()
        if prov not in ("gemini", "groq"):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported provider: '{req.provider}'. Must be 'gemini' or 'groq'."
            )
        settings.llm_provider = prov

    if req.model:
        if settings.llm_provider == "groq":
            settings.groq_model = req.model
        else:
            settings.gemini_model = req.model

    if req.api_key:
        if settings.llm_provider == "groq":
            settings.groq_api_key = req.api_key
        else:
            settings.gemini_api_key = req.api_key

    return get_settings()


@router.post("/test", response_model=TestConnectionResponse)
def test_connection(req: TestConnectionRequest):
    """
    Test live connectivity and quota health with a fast 1-token diagnostic ping.
    Returns success status and latency in ms, or human-readable quota/connection failure reason.
    """
    prov = req.provider.lower()
    if prov not in ("gemini", "groq"):
        return TestConnectionResponse(
            success=False,
            message=f"Unsupported provider: '{req.provider}'",
        )

    # Temporarily evaluate with custom key if provided
    key = req.api_key or (settings.groq_api_key if prov == "groq" else settings.gemini_api_key)
    if not key:
        return TestConnectionResponse(
            success=False,
            message=f"{req.provider.upper()} API key is not configured. Please supply a key.",
        )

    start = time.perf_counter()
    try:
        call_structured_llm(
            prompt="Respond with JSON: {\"status\": \"ok\"}",
            system_instruction="Health ping responder. Output valid JSON.",
            response_schema=PingResult,
            provider=prov,
            model=req.model,
            api_key=key,
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return TestConnectionResponse(
            success=True,
            latency_ms=elapsed_ms,
            message=f"Connected to {req.provider.upper()} ({req.model}) in {elapsed_ms}ms",
        )
    except Exception as exc:
        err_msg = str(exc)
        if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "quota" in err_msg.lower():
            friendly = (
                f"{req.provider.upper()} Quota Exceeded (429 Rate Limit): "
                "Daily free request quota for this model has been exhausted."
            )
        elif "Groq Error" in err_msg or "model_not_found" in err_msg:
            friendly = f"Groq Error: {err_msg}"
        else:
            friendly = f"Connection failed: {err_msg[:240]}"

        return TestConnectionResponse(
            success=False,
            message=friendly,
        )

