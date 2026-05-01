from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = PROJECT_ROOT / "frontend"

load_dotenv(PROJECT_ROOT / ".env")

LOCAL_MODEL_NAME = os.getenv("LOCAL_MODEL_NAME", "gemma4")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_GENERATE_URL = f"{OLLAMA_BASE_URL}/api/generate"
OLLAMA_TAGS_URL = f"{OLLAMA_BASE_URL}/api/tags"


class Direction(str, Enum):
    PROFESSOR_TO_GENZ = "professor_to_genz"
    GENZ_TO_PROFESSOR = "genz_to_professor"


class ToneLevel(str, Enum):
    LIGHT_GENZ = "light_genz"
    MEDIUM_GENZ = "medium_genz"
    EXTREME_GENZ = "extreme_genz"
    PROFESSIONAL_ACADEMIC = "professional_academic"


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=6000)
    direction: Direction
    tone_level: ToneLevel
    explain_slang: bool = False

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Text cannot be blank.")
        return stripped


class TranslateResponse(BaseModel):
    translation: str
    model: str
    direction: Direction
    tone_level: ToneLevel


class HealthResponse(BaseModel):
    ok: bool
    model: str
    ollama_base_url: str
    message: str


app = FastAPI(
    title="GenZ Translator",
    description="A local professor-to-Gen-Z translator powered by Ollama.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    try:
        await ensure_model_available()
    except HTTPException as exc:
        return HealthResponse(
            ok=False,
            model=LOCAL_MODEL_NAME,
            ollama_base_url=OLLAMA_BASE_URL,
            message=str(exc.detail),
        )

    return HealthResponse(
        ok=True,
        model=LOCAL_MODEL_NAME,
        ollama_base_url=OLLAMA_BASE_URL,
        message="Ollama is reachable and the configured model is available.",
    )


@app.post("/translate", response_model=TranslateResponse)
async def translate(request: TranslateRequest) -> TranslateResponse:
    prompt = build_prompt(request)

    payload: dict[str, Any] = {
        "model": LOCAL_MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature_for_tone(request.tone_level),
            "top_p": 0.9,
            "num_predict": 900,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(OLLAMA_GENERATE_URL, json=payload)
    except httpx.ConnectError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Could not reach Ollama at "
                f"{OLLAMA_BASE_URL}. Start Ollama, then try again."
            ),
        ) from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="The local model took too long to respond. Try a shorter text or a smaller model.",
        ) from exc

    if response.status_code == 404:
        raise HTTPException(
            status_code=503,
            detail=(
                f"The model '{LOCAL_MODEL_NAME}' is not available in Ollama. "
                f"Run: ollama pull {LOCAL_MODEL_NAME}"
            ),
        )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama returned an error: {response.text}",
        )

    data = response.json()
    translated_text = (data.get("response") or "").strip()

    if not translated_text:
        raise HTTPException(
            status_code=502,
            detail="The local model returned an empty response. Please try again.",
        )

    return TranslateResponse(
        translation=translated_text,
        model=LOCAL_MODEL_NAME,
        direction=request.direction,
        tone_level=request.tone_level,
    )


async def ensure_model_available() -> None:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(OLLAMA_TAGS_URL)
    except httpx.ConnectError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Ollama is not reachable. Make sure the Ollama app or service is running "
                f"at {OLLAMA_BASE_URL}."
            ),
        ) from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="Ollama did not respond to the health check in time.",
        ) from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama health check failed: {response.text}",
        )

    models = response.json().get("models", [])
    available_names = {model.get("name", "") for model in models}
    available_roots = {name.split(":")[0] for name in available_names}
    requested_root = LOCAL_MODEL_NAME.split(":")[0]

    if LOCAL_MODEL_NAME not in available_names and requested_root not in available_roots:
        raise HTTPException(
            status_code=503,
            detail=(
                f"The configured model '{LOCAL_MODEL_NAME}' is not installed. "
                f"Install it with: ollama pull {LOCAL_MODEL_NAME}"
            ),
        )


def build_prompt(request: TranslateRequest) -> str:
    direction_prompt = (
        professor_to_genz_prompt(request.tone_level)
        if request.direction == Direction.PROFESSOR_TO_GENZ
        else genz_to_professor_prompt()
    )

    explanation_instruction = (
        "After the translation, add a short section titled 'Slang explanation' that explains "
        "the slang or idioms in plain English. Keep it concise and useful."
        if request.explain_slang
        else "Return only the translated text. Do not add explanations, labels, or commentary."
    )

    return f"""
You are GenZ Translator, a careful translation assistant for college professors.

{direction_prompt}

Tone setting: {tone_label(request.tone_level)}
Additional instruction: {explanation_instruction}

Input text:
\"\"\"{request.text}\"\"\"

Output:
""".strip()


def professor_to_genz_prompt(tone_level: ToneLevel) -> str:
    intensity = {
        ToneLevel.LIGHT_GENZ: (
            "Use light, natural Gen Z phrasing. Keep most academic structure intact, "
            "with only a few current casual expressions."
        ),
        ToneLevel.MEDIUM_GENZ: (
            "Use a balanced Gen Z voice that feels student-friendly and readable. "
            "Include contemporary slang where it clarifies tone, but avoid overloading every sentence."
        ),
        ToneLevel.EXTREME_GENZ: (
            "Use a high-energy Gen Z style while preserving the exact meaning. "
            "Make it playful, but still understandable to a student reading course instructions."
        ),
        ToneLevel.PROFESSIONAL_ACADEMIC: (
            "Keep the result polished and academic. Since this tone is selected, avoid slang and "
            "produce a clearer formal rewrite instead."
        ),
    }[tone_level]

    return f"""
Translate professor or formal academic language into Gen Z student language.
Rules:
- Preserve the original meaning, requirements, constraints, and level of seriousness.
- Make the text sound natural to current Gen Z college students.
- Avoid cringe, forced, dated, or meme-only slang.
- Keep instructions readable and respectful.
- Do not introduce new facts or change deadlines, grades, policies, or expectations.
- {intensity}
""".strip()


def genz_to_professor_prompt() -> str:
    return """
Translate Gen Z slang into professor-ready formal academic English.
Rules:
- Preserve the original meaning, sentiment, and intensity.
- Convert slang, idioms, abbreviations, and casual phrasing into clear professional language.
- Explain implied meaning when needed without sounding judgmental.
- Keep the tone polished, respectful, concise, and suitable for a classroom or faculty setting.
- Do not introduce new facts or soften meaningful criticism unless it becomes disrespectful.
""".strip()


def tone_label(tone_level: ToneLevel) -> str:
    labels = {
        ToneLevel.LIGHT_GENZ: "Light Gen Z",
        ToneLevel.MEDIUM_GENZ: "Medium Gen Z",
        ToneLevel.EXTREME_GENZ: "Extreme Gen Z",
        ToneLevel.PROFESSIONAL_ACADEMIC: "Professional Academic",
    }
    return labels[tone_level]


def temperature_for_tone(tone_level: ToneLevel) -> float:
    temperatures = {
        ToneLevel.LIGHT_GENZ: 0.45,
        ToneLevel.MEDIUM_GENZ: 0.65,
        ToneLevel.EXTREME_GENZ: 0.85,
        ToneLevel.PROFESSIONAL_ACADEMIC: 0.35,
    }
    return temperatures[tone_level]
