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
from case_store import auto_save_enabled, delete_case, list_cases, save_case
from interactive_jobs import list_jobs, start_interactive_build


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
    base_url = str(request.base_url)
    result = service.generate(payload, base_url=base_url)

    # 自动沉淀为展厅可直接展示的案例。
    # 保存是副作用：任何异常都只记录在响应里，绝不改变已经成功的出图结果。
    if auto_save_enabled() and isinstance(result, dict) and result.get("success"):
        try:
            saved = save_case(payload=payload, response=result, base_url=base_url)
            result["savedCase"] = saved
            result["autoSave"] = {"enabled": True, "saved": bool(saved), "error": None}
            # 落盘之后顺手把「三重互动」也做出来：三折叙事 + 自动热点 + 画境资产。
            # 深度推理要十几秒，绝不能阻塞这次出图响应，所以丢到后台线程里跑；
            # 跑完 ingest 会把 metadata.json 的 experienceId 写回去，前端下次加载就能用。
            if saved and saved.get("caseId"):
                result["interactiveJob"] = start_interactive_build(str(saved["caseId"]))
        except Exception as exc:  # noqa: BLE001 - 保存失败不能影响出图
            result["savedCase"] = None
            result["autoSave"] = {"enabled": True, "saved": False, "error": f"{type(exc).__name__}: {str(exc)[:160]}"}
    else:
        result["savedCase"] = None
        result["autoSave"] = {"enabled": False, "saved": False, "error": None}
    return result


@app.get("/cases")
def cases(request: Request) -> dict[str, object]:
    """展厅用的案例清单：内置五件 + 运行期自动保存的案例，含可直接使用的图片地址。"""
    items = list_cases(base_url=str(request.base_url))
    return {
        "success": True,
        "count": len(items),
        "cases": items,
        "error": None,
    }


@app.get("/interactive-jobs")
def interactive_jobs() -> dict[str, object]:
    """出图后自动生成「三折叙事 + 热点 + 画境」的后台任务状态。

    任务跑完会把 experienceId 写进案例的 metadata.json；前端重新构建/重启开发服务器后
    该案例的卡片上就会出现三个互动入口。
    """
    jobs = list_jobs()
    return {"success": True, "count": len(jobs), "jobs": jobs, "error": None}


@app.delete("/cases/{case_id}")
def remove_case(case_id: str) -> dict[str, object]:
    """删除运行期案例；内置的真实案例受保护，不允许删除。"""
    removed = delete_case(case_id)
    if not removed:
        raise HTTPException(status_code=400, detail="只能删除运行期自动保存的案例（内置案例受保护）")
    return {"success": True, "caseId": case_id}
