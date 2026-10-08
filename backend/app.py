from __future__ import annotations

from typing import Any, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from image_analyzer import analyze_image, get_analysis_mode
from provider_service import GenerationService
from style_config import OUTPUT_DIR, STYLE_REFS_DIR, ensure_runtime_dirs


class GenerateRequest(BaseModel):
    theme: str = Field(..., min_length=1, max_length=1200)
    style: str = Field(default="zhuxianzhen")
    styleName: str = Field(default="")
    outputType: str = Field(default="poster")
    styleStrength: float = Field(default=0.65, ge=0, le=1.5)
    compositionMode: str = Field(default="portrait")
    negativePrompt: Optional[str] = Field(default=None)
    subjectLock: Optional[str] = Field(default=None, max_length=120)
    uploadedImage: Optional[str] = Field(default=None)
    generationProvider: Optional[str] = Field(default=None, pattern="^(dashscope_qwen_image|instantstyle)$")


class AnalyzeImageRequest(BaseModel):
    uploadedImage: Optional[str] = Field(default=None)


ensure_runtime_dirs()

app = FastAPI(
    title="纹脉华章 AI 图像生成后端",
    version="0.3.0",
    description="FastAPI backend for DashScope Qwen Image generation with text and reference-image input.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="outputs")
app.mount("/style_refs", StaticFiles(directory=str(STYLE_REFS_DIR)), name="style_refs")

app.mount("/examples", StaticFiles(directory=str(Path(__file__).resolve().parents[1] / "docs/examples")), name="examples")

service = GenerationService()


@app.get("/health")
def health() -> dict[str, object]:
    return service.health()


@app.post("/analyze-image")
def analyze_image_endpoint(request_body: AnalyzeImageRequest) -> dict[str, object]:
    try:
        analysis = analyze_image(request_body.uploadedImage)
        return {
            "success": True,
            "analysis": analysis,
            "mode": get_analysis_mode(),
            "error": None,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/generate")
def generate(request_body: GenerateRequest, request: Request) -> dict[str, Any]:
    payload = request_body.model_dump() if hasattr(request_body, "model_dump") else request_body.dict()
    return service.generate(payload, base_url=str(request.base_url))
