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
from case_store import (
    archive_runtime_case,
    auto_save_enabled,
    get_case,
    list_cases,
    load_experience,
    save_case,
)
from interactive_jobs import get_job, list_jobs, start_interactive_build, idle_case_mutation, InteractiveJobBusy


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


@app.middleware('http')
async def preserve_asset_cors_variant(request: Request, call_next):
    response = await call_next(request)
    # Browsers first show these as <img>, then load them as WebGL textures.
    # Plain image requests carry no Origin. They must not cache a response that
    # masks the CORS-enabled variant required by the later texture request.
    if request.url.path.startswith(('/examples/', '/outputs/', '/style_refs/', '/interactive/')):
        vary = [item.strip() for item in response.headers.get('vary', '').split(',') if item.strip()]
        if not any(item.lower() == 'origin' for item in vary):
            response.headers['Vary'] = ', '.join(vary + ['Origin'])
    return response

app.mount("/outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="outputs")
app.mount("/style_refs", StaticFiles(directory=str(STYLE_REFS_DIR)), name="style_refs")

app.mount("/examples", StaticFiles(directory=str(Path(__file__).resolve().parents[1] / "docs/examples")), name="examples")
app.mount('/interactive', StaticFiles(directory=str(Path(__file__).resolve().parents[1] / 'frontend/public/interactive')), name='interactive')

service = GenerationService()


@app.get("/health")
def health() -> dict[str, object]:
    import os
    from services.deepseek_review import ReviewClient,ConfigurationError
    result=service.health()
    enabled=os.getenv('DEEPSEEK_REVIEW_ENABLED','false').lower() in ('true','1','yes','on')
    try:
        reviewer=ReviewClient.from_env()
        result['deepseekReview']={'enabled':enabled,'configured':True,'provider':reviewer.provider,
            'model':reviewer.model,'note':'配置检查，不执行收费请求；实际评价见各作品复审记录。'}
    except ConfigurationError:
        result['deepseekReview']={'enabled':enabled,'configured':False,'note':'请检查后端DeepSeek配置，不输出密钥。'}
    return result


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
            # 本地 Qwen3-VL 解析与画境资产在后台构建，不阻塞返回已保存的作品；
            # 展厅轮询最新状态，完成后自动出现三个入口，无需重启前端。
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
    """作品展厅用的案例清单：内置精选 + 运行期自动保存，含互动构建状态。"""
    items = list_cases(base_url=str(request.base_url))
    jobs = {str(job.get("caseId")): job for job in list_jobs()}
    for item in items:
        item["interaction"] = _interaction_summary(item, jobs.get(str(item.get("caseId"))))
    return {
        "success": True,
        "count": len(items),
        "cases": items,
        "error": None,
    }


def _interaction_summary(case: dict[str, Any], job: dict[str, Any] | None) -> dict[str, Any]:
    """把「磁盘上真实有什么」与「后台任务在哪一步」合并成一个状态。

    前端只认这个结构，避免再按 styleId 猜互动是否存在。
    """
    has_experience = bool(case.get("hasExperience"))
    has_world = bool(case.get("hasWorld"))
    job_status = str((job or {}).get("status") or "")
    metadata_status = str(((case.get("metadata") or {}).get("interactive") or {}).get("status") or "")

    if job_status in {"queued", "processing"}:
        status = job_status
    elif job_status == "failed":
        status = "failed"
    elif has_experience and has_world:
        status = "ready"
    elif has_experience:
        status = "partial"
    elif job_status in {"failed", "ready", "partial"}:
        status = job_status
    elif metadata_status in {"ready", "partial"}:
        status = metadata_status
    else:
        status = "none"

    return {
        "status": status,
        "stages": {
            "hotspots": has_experience,
            "story": has_experience,
            "world": has_world,
        },
        "hasExperience": has_experience,
        "hasWorld": has_world,
        "experienceId": str(case.get("experienceId") or ""),
        "job": job,
        "qualityReview":case.get('qualityReview') or (case.get('metadata') or {}).get('qualityReview') or {},
    }


@app.get("/cases/{case_id}")
def case_detail(case_id: str, request: Request) -> dict[str, object]:
    """单件作品：图片/参考图/文化卡 + 它自己的 experience.json + 任务状态。

    这是前端运行期互动体验的唯一入口，作品身份严格由 caseId 决定。
    """
    case = get_case(case_id, base_url=str(request.base_url))
    if not case:
        raise HTTPException(status_code=404, detail="作品不存在")
    job = get_job(case_id)
    experience = load_experience(case_id)
    return {
        "success": True,
        "case": case,
        "experience": experience,
        "interaction": _interaction_summary(case, job),
        "error": None,
    }


@app.post("/cases/{case_id}/interactions/rebuild")
def rebuild_interactions(case_id: str, request: Request) -> dict[str, object]:
    """重新构建三种互动。只允许运行期案例，内置精选内容不可被覆盖。"""
    case = get_case(case_id, base_url=str(request.base_url))
    if not case:
        raise HTTPException(status_code=404, detail="作品不存在")
    if str((case.get("metadata") or {}).get("caseOrigin")) != "runtime":
        raise HTTPException(status_code=400, detail="内置精选作品的互动内容受保护，不能重建")
    job = start_interactive_build(case_id, force=True)
    if not job.get("enabled", True):
        raise HTTPException(status_code=400, detail=str(job.get("status")))
    return {"success": True, "caseId": case_id, "job": job, "error": None}


@app.get("/interactive-jobs")
def interactive_jobs() -> dict[str, object]:
    """出图后自动生成「三折叙事 + 热点 + 画境」的后台任务状态。

    任务跑完会把 experienceId 写进案例的 metadata.json；展厅自动回读最新状态，
    无需重新构建或重启前端即可出现三个互动入口。
    """
    jobs = list_jobs()
    return {"success": True, "count": len(jobs), "jobs": jobs, "error": None}


@app.delete("/cases/{case_id}")
def remove_case(case_id: str) -> dict[str, object]:
    """删除运行期案例；内置的真实案例受保护，不允许删除。"""
    try:
        with idle_case_mutation(case_id):
            if not archive_runtime_case(case_id):
                raise HTTPException(status_code=400, detail="只能删除运行期自动保存的案例（内置案例受保护）")
    except InteractiveJobBusy as exc:
        raise HTTPException(status_code=409,detail=str(exc)) from exc
    return {"success": True, "caseId": case_id}
