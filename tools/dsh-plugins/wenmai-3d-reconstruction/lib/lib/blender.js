/**
 * Blender job runner: writes a job JSON, spawns headless Blender, enforces
 * timeouts / cooperative cancellation, then reads the structured result file.
 *
 * The plugin never parses Blender's stdout for data — only for the failure
 * tail. Contract: docs/CONTRACT.md §2.
 */
import { spawn } from 'node:child_process';
import { createWriteStream, existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { assertBlender, PathViolation, resolveInsideProject } from './config.js';
import { pruneUndefined } from './result.js';
export class ToolRuntimeError extends Error {
    code;
    detail;
    constructor(code, message, detail) {
        super(message);
        this.name = 'ToolRuntimeError';
        this.code = code;
        this.detail = detail;
    }
}
const RESULT_TAIL_BYTES = 64 * 1024;
function timestamp() {
    const d = new Date();
    const pad = (n, w = 2) => String(n).padStart(w, '0');
    return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
}
export function makeJobId(task) {
    const rand = Math.random().toString(36).slice(2, 6);
    return `${timestamp()}-${task}-${rand}`;
}
/** Write the job JSON and return its paths. All paths stay inside the project. */
export function createJob(cfg, task, params, opts = {}) {
    const jobId = makeJobId(task);
    const workDir = path.join(cfg.jobsDir, jobId);
    const resultPath = path.join(workDir, 'result.json');
    const logPath = path.join(workDir, 'blender.log');
    const jobPath = path.join(workDir, 'job.json');
    mkdirSync(workDir, { recursive: true });
    mkdirSync(cfg.sceneDir, { recursive: true });
    mkdirSync(cfg.rendersDir, { recursive: true });
    mkdirSync(cfg.reportsDir, { recursive: true });
    const baseBlend = opts.baseBlend === null
        ? null
        : opts.baseBlend
            ? path.isAbsolute(opts.baseBlend)
                ? path.resolve(opts.baseBlend)
                : resolveInsideProject(cfg, opts.baseBlend, 'baseBlend')
            : null;
    const outBlend = opts.outBlend
        ? path.isAbsolute(opts.outBlend)
            ? path.resolve(opts.outBlend)
            : resolveInsideProject(cfg, opts.outBlend, 'outBlend')
        : path.join(cfg.sceneDir, 'wenmai_scene.blend');
    const context = {
        projectRoot: cfg.projectRoot,
        workDir,
        resultPath,
        sceneDir: cfg.sceneDir,
        rendersDir: cfg.rendersDir,
        reportsDir: cfg.reportsDir,
        referencesDir: cfg.referencesDir,
        blenderExe: cfg.blenderExe,
        baseBlend,
        outBlend,
        pluginDir: path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..'),
        ...(opts.extraContext ?? {}),
    };
    const job = { task, jobId, params, context };
    writeFileSync(jobPath, JSON.stringify(job, null, 2), 'utf8');
    return { jobId, jobPath, resultPath, logPath, workDir };
}
function pythonEntry() {
    // lib/ -> plugin root, then python/wm_job.py
    const here = path.dirname(fileURLToPath(import.meta.url));
    return path.resolve(here, '..', '..', 'python', 'wm_job.py');
}
/** Wait for the child, enforcing a deadline and observing the caller signal. */
function awaitChild(child, timeoutMs, signal) {
    return new Promise((resolve, reject) => {
        let settled = false;
        let killReason = null;
        const finish = (fn) => {
            if (settled)
                return;
            settled = true;
            cleanup();
            fn();
        };
        const killTree = () => {
            const pid = child.pid;
            if (!pid)
                return;
            try {
                child.kill('SIGTERM');
            }
            catch {
                /* ignore */
            }
            try {
                // SIGTERM does not always reach a Windows console app; be explicit.
                spawn('taskkill', ['/PID', String(pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' });
            }
            catch {
                /* ignore */
            }
        };
        const timer = setTimeout(() => {
            killReason = 'timeout';
            killTree();
        }, Math.max(1000, timeoutMs));
        const onAbort = () => {
            killReason = 'abort';
            killTree();
        };
        const cleanup = () => {
            clearTimeout(timer);
            signal?.removeEventListener('abort', onAbort);
        };
        if (signal) {
            if (signal.aborted)
                onAbort();
            else
                signal.addEventListener('abort', onAbort, { once: true });
        }
        child.on('error', (error) => {
            finish(() => reject(new ToolRuntimeError('SPAWN_FAILED', error.message)));
        });
        child.on('close', (code) => {
            if (killReason === 'abort') {
                finish(() => reject(new ToolRuntimeError('ABORTED', 'Blender job cancelled by the caller')));
                return;
            }
            if (killReason === 'timeout') {
                finish(() => reject(new ToolRuntimeError('TOOL_TIMEOUT', `Blender job exceeded ${timeoutMs} ms and was stopped`)));
                return;
            }
            finish(() => resolve(code ?? -1));
        });
    });
}
/** Read the result file even when Blender reported a non-zero exit. */
function readResult(resultPath) {
    if (!existsSync(resultPath))
        return null;
    try {
        const text = readFileSync(resultPath, 'utf8');
        if (!text.trim())
            return null;
        return JSON.parse(text);
    }
    catch (error) {
        throw new ToolRuntimeError('BAD_RESULT', `cannot parse Blender result JSON: ${error.message}`);
    }
}
function normaliseArtifacts(cfg, raw) {
    if (!Array.isArray(raw))
        return [];
    const out = [];
    for (const item of raw) {
        if (!item || typeof item !== 'object')
            continue;
        const entry = item;
        const p = typeof entry.path === 'string' ? entry.path : '';
        if (!p)
            continue;
        const resolved = path.resolve(p);
        let exists = false;
        let bytes = 0;
        try {
            exists = statSync(resolved).isFile();
            if (exists)
                bytes = statSync(resolved).size;
        }
        catch {
            exists = false;
        }
        const relative = path.relative(cfg.projectRoot, resolved);
        const outside = relative.startsWith('..') || path.isAbsolute(relative);
        if (outside) {
            throw new PathViolation(`artifact outside the authorized project root: ${resolved}`);
        }
        out.push({
            kind: typeof entry.kind === 'string' ? entry.kind : 'file',
            path: resolved,
            bytes,
            exists,
            relativePath: relative.replace(/\\/g, '/'),
        });
    }
    return out;
}
function normaliseChecks(raw) {
    if (!Array.isArray(raw))
        return [];
    const allowed = new Set(['pass', 'warn', 'fail', 'manual', 'not_checked']);
    const out = [];
    for (const item of raw) {
        if (!item || typeof item !== 'object')
            continue;
        const entry = item;
        const status = typeof entry.status === 'string' && allowed.has(entry.status) ? entry.status : 'not_checked';
        out.push({
            ...entry,
            id: typeof entry.id === 'string' ? entry.id : 'unnamed',
            status: status,
            detail: typeof entry.detail === 'string' ? entry.detail : '',
        });
    }
    return out;
}
/**
 * Run one Blender task and return its normalised result.
 * Throws ToolRuntimeError with a stable code on failure/cancellation.
 */
export async function runBlenderTask(cfg, task, params, opts = {}) {
    const blender = assertBlender(cfg);
    if (opts.baseBlend !== null && opts.baseBlend !== undefined) {
        const base = path.resolve(opts.baseBlend);
        if (!existsSync(base))
            throw new ToolRuntimeError('BASE_MISSING', `baseBlend does not exist: ${base}`);
        resolveInsideProject(cfg, base, 'baseBlend');
    }
    const handle = createJob(cfg, task, params, opts);
    const args = ['-b'];
    if (opts.baseBlend)
        args.push(path.resolve(opts.baseBlend));
    args.push('-noaudio', '--python', pythonEntry(), '--', handle.jobPath);
    const started = Date.now();
    const logStream = createWriteStream(handle.logPath, { flags: 'w' });
    logStream.write(`# ${new Date().toISOString()}\n# ${blender} ${args.join(' ')}\n`);
    const tail = [];
    let tailBytes = 0;
    const capture = (chunk, channel) => {
        const text = chunk.toString('utf8');
        logStream.write(text);
        if (tailBytes < RESULT_TAIL_BYTES) {
            tail.push(channel + text);
            tailBytes += text.length;
        }
    };
    const child = spawn(blender, args, {
        windowsHide: true,
        stdio: ['ignore', 'pipe', 'pipe'],
        env: { ...process.env, WM_PROJECT_ROOT: cfg.projectRoot, WM_JOB_DIR: handle.workDir },
    });
    child.stdout?.on('data', (c) => capture(c, ''));
    child.stderr?.on('data', (c) => capture(c, '[stderr] '));
    let exitCode;
    try {
        exitCode = await awaitChild(child, opts.timeoutMs ?? cfg.timeoutMs, opts.signal);
    }
    finally {
        await new Promise((resolve) => logStream.end(resolve));
    }
    const durationMs = Date.now() - started;
    const result = readResult(handle.resultPath);
    if (!result) {
        const tailText = tail.join('').slice(-6000);
        throw new ToolRuntimeError(exitCode === 0 ? 'NO_RESULT' : 'BLENDER_FAILED', `Blender produced no result file (exit ${exitCode}). Log: ${handle.logPath}\n${tailText}`, { logPath: handle.logPath, exitCode });
    }
    const normalised = {
        ok: result.ok !== false,
        task: typeof result.task === 'string' ? result.task : task,
        jobId: typeof result.jobId === 'string' ? result.jobId : handle.jobId,
        durationMs,
        artifacts: normaliseArtifacts(cfg, result.artifacts),
        objects: Array.isArray(result.objects) ? result.objects : undefined,
        metrics: result.metrics ?? undefined,
        checks: normaliseChecks(result.checks),
        warnings: Array.isArray(result.warnings) ? result.warnings.map(String) : [],
        notes: typeof result.notes === 'string' ? result.notes : '',
        logPath: handle.logPath,
        ...result,
    };
    normalised.artifacts = normaliseArtifacts(cfg, result.artifacts);
    normalised.checks = normaliseChecks(result.checks);
    normalised.durationMs = durationMs;
    normalised.logPath = handle.logPath;
    if (!normalised.ok) {
        const error = result.error?.message ?? 'task reported ok=false';
        throw new ToolRuntimeError('TASK_FAILED', `${task} failed: ${error}`, {
            logPath: handle.logPath,
            resultPath: handle.resultPath,
        });
    }
    if (exitCode !== 0) {
        normalised.warnings.push(`Blender exited with code ${exitCode} but reported ok=true`);
    }
    // The registry rejects values that are not lossless JSON; `undefined` members
    // (e.g. an absent `objects`/`metrics`) must be pruned before returning.
    return pruneUndefined(normalised);
}
