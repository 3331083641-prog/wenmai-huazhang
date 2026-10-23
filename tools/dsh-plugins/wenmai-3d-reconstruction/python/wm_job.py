"""Blender entry point for every wenmai-3d-reconstruction job.

Usage (from the plugin's Node runner):

    blender.exe -b [<base.blend>] -noaudio --python wm_job.py -- <job.json>

The job JSON is described in docs/CONTRACT.md. The dispatch table below is the
only place that maps a task name to a Python function; every function has the
signature ``fn(params: dict, ctx: dict) -> dict``.
"""
from __future__ import annotations

import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import wm_common  # noqa: E402  (path set above)


# task name -> (module, function)
TASKS = {
    # B — parametric generation
    "generate_roof": ("wm_roof", "generate_roof"),
    "generate_timber": ("wm_timber", "generate_timber"),
    "generate_interior": ("wm_interior", "generate_interior"),
    "generate_diorama": ("wm_diorama", "generate_diorama"),
    "export_glb": ("wm_export", "export_glb"),
    # A — reference reconstruction
    "analyze_references": ("wm_analysis", "analyze_references"),
    "match_camera": ("wm_camera", "match_camera"),
    "validate_multiview": ("wm_camera", "validate_multiview"),
    # C — visual matching
    "capture_views": ("wm_capture", "capture_views"),
    "compare_reference": ("wm_compare", "compare_reference"),
    "propose_geometry_changes": ("wm_compare", "propose_geometry_changes"),
    # D — inspection
    "inspect_scene": ("wm_inspect", "inspect_scene"),
    "check_art_frames": ("wm_inspect", "check_art_frames"),
    "check_export": ("wm_inspect", "check_export"),
    "performance_report": ("wm_inspect", "performance_report"),
}


def main() -> int:
    job = wm_common.read_job()
    task = job.get("task")
    ctx = job.get("context") or {}
    ctx.setdefault("pluginDir", HERE)
    ctx["task"] = task
    ctx["jobId"] = job.get("jobId")

    entry = TASKS.get(task)
    if entry is None:
        wm_common.write_result(job, wm_common.fail(f"unknown task: {task}", task=task))
        return 2

    module_name, func_name = entry
    wm_common.log(f"task={task} job={job.get('jobId')} module={module_name}")
    try:
        module = __import__(module_name, fromlist=[func_name])
        fn = getattr(module, func_name)
        result = fn(job.get("params") or {}, ctx)
        if result is None:
            result = wm_common.fail(f"{module_name}.{func_name} returned None")
        wm_common.write_result(job, result)
        return 0 if result.get("ok", True) else 1
    except Exception:
        detail = traceback.format_exc()
        wm_common.log("FAILED\n" + detail)
        wm_common.write_result(job, wm_common.fail(detail))
        return 1
    finally:
        # Blender would otherwise keep a background process alive on some
        # Windows builds when a task leaks a compositor/EEVEE handle.
        sys.stdout.flush()
        sys.stderr.flush()


if __name__ == "__main__":
    raise SystemExit(main())
