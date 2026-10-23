import type { JsonValue } from './sdk.js';
import { type ResolvedConfig } from './config.js';
export type TaskName = 'analyze_references' | 'match_camera' | 'validate_multiview' | 'generate_roof' | 'generate_timber' | 'generate_interior' | 'generate_diorama' | 'export_glb' | 'capture_views' | 'compare_reference' | 'propose_geometry_changes' | 'inspect_scene' | 'check_art_frames' | 'check_export' | 'performance_report';
export interface Artifact {
    kind: string;
    path: string;
    bytes: number;
    exists: boolean;
    relativePath?: string;
    outsideProject?: boolean;
}
export interface ToolCheck {
    id: string;
    status: 'pass' | 'warn' | 'fail' | 'manual' | 'not_checked';
    detail: string;
    [key: string]: unknown;
}
export interface TaskResult {
    ok: boolean;
    task: string;
    jobId: string;
    durationMs: number;
    artifacts: Artifact[];
    objects?: unknown[];
    metrics?: Record<string, JsonValue>;
    checks: ToolCheck[];
    warnings: string[];
    notes: string;
    logPath: string;
    [key: string]: unknown;
}
export interface RunOptions {
    baseBlend?: string | null;
    outBlend?: string | null;
    timeoutMs?: number;
    signal?: AbortSignal;
    extraContext?: Record<string, unknown>;
}
export declare class ToolRuntimeError extends Error {
    code: string;
    detail?: Record<string, unknown>;
    constructor(code: string, message: string, detail?: Record<string, unknown>);
}
export declare function makeJobId(task: string): string;
export interface JobHandle {
    jobId: string;
    jobPath: string;
    resultPath: string;
    logPath: string;
    workDir: string;
}
/** Write the job JSON and return its paths. All paths stay inside the project. */
export declare function createJob(cfg: ResolvedConfig, task: TaskName, params: Record<string, unknown>, opts?: RunOptions): JobHandle;
/**
 * Run one Blender task and return its normalised result.
 * Throws ToolRuntimeError with a stable code on failure/cancellation.
 */
export declare function runBlenderTask(cfg: ResolvedConfig, task: TaskName, params: Record<string, unknown>, opts?: RunOptions): Promise<TaskResult>;
