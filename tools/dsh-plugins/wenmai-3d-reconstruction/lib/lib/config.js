/**
 * Configuration and path safety for the wenmai-3d-reconstruction plugin.
 *
 * Every path a tool reads or writes must resolve inside the authorized project
 * root (`D:\wenmai-huazhang` by default). The single exception is the Blender
 * executable, which is an installed application outside the project.
 */
import { existsSync, statSync } from 'node:fs';
import path from 'node:path';
export const DEFAULT_PROJECT_ROOT = 'D:\\wenmai-huazhang';
export const DEFAULT_BLENDER_EXE = 'D:\\Codex\\blender-5.2.2\\blender-5.2.2-windows-x64\\blender.exe';
function isDirectory(p) {
    try {
        return statSync(p).isDirectory();
    }
    catch {
        return false;
    }
}
function isFile(p) {
    try {
        return statSync(p).isFile();
    }
    catch {
        return false;
    }
}
/** Resolve plugin config into absolute paths, filling documented defaults. */
export function resolveConfig(config) {
    const projectRoot = path.resolve(config?.projectRoot?.trim() || DEFAULT_PROJECT_ROOT);
    const workRoot = path.resolve(config?.workRoot?.trim() || path.join(projectRoot, 'outputs', 'wenmai-3d'));
    const jobsDir = path.join(workRoot, 'jobs');
    return {
        projectRoot,
        blenderExe: path.resolve(config?.blenderExe?.trim() || DEFAULT_BLENDER_EXE),
        timeoutMs: clampNumber(config?.timeoutMs, 30_000, 7_200_000, 1_800_000),
        workRoot,
        referencesDir: path.resolve(config?.referencesDir?.trim() || path.join(projectRoot, 'assets', 'gallery3d', 'references', 'raw')),
        baseBlend: path.resolve(config?.baseBlend?.trim() || path.join(projectRoot, 'assets', 'gallery3d', 'blender', 'wenmai_gallery_v5.blend')),
        jobsDir,
        sceneDir: path.join(workRoot, 'scene'),
        rendersDir: path.join(workRoot, 'renders'),
        reportsDir: path.join(workRoot, 'reports'),
        allowProjectWrites: config?.allowProjectWrites !== false,
    };
}
function clampNumber(value, min, max, fallback) {
    const n = typeof value === 'number' && Number.isFinite(value) ? value : Number.NaN;
    if (!Number.isFinite(n))
        return fallback;
    return Math.max(min, Math.min(max, Math.round(n)));
}
/** Thrown by path validation; surfaced as a structured tool error. */
export class PathViolation extends Error {
    constructor(message) {
        super(message);
        this.name = 'PathViolation';
    }
}
function within(root, candidate) {
    const rel = path.relative(root, candidate);
    return rel === '' || (!rel.startsWith('..') && !path.isAbsolute(rel));
}
/**
 * Resolve a user/model supplied path and require it to stay inside the project
 * root. Relative paths resolve against the project root.
 */
export function resolveInsideProject(cfg, input, label = 'path') {
    if (typeof input !== 'string' || input.trim() === '') {
        throw new PathViolation(`${label} must be a non-empty string`);
    }
    const resolved = path.isAbsolute(input) ? path.resolve(input) : path.resolve(cfg.projectRoot, input);
    if (!within(cfg.projectRoot, resolved)) {
        throw new PathViolation(`${label} is outside the authorized project root: ${input} (root: ${cfg.projectRoot})`);
    }
    return resolved;
}
/** Resolve an existing input file inside the project root. */
export function requireProjectFile(cfg, input, label = 'file') {
    const resolved = resolveInsideProject(cfg, input, label);
    if (!isFile(resolved))
        throw new PathViolation(`${label} does not exist: ${resolved}`);
    return resolved;
}
/** Resolve an output directory inside the project root, creating it later. */
export function resolveOutputDir(cfg, input, fallback) {
    if (!input || input.trim() === '')
        return fallback;
    return resolveInsideProject(cfg, input, 'outDir');
}
/** Validate the configured Blender executable (allowed outside the root). */
export function assertBlender(cfg) {
    if (!isFile(cfg.blenderExe)) {
        throw new Error(`Blender executable not found: ${cfg.blenderExe} (configure blenderExe)`);
    }
    return cfg.blenderExe;
}
/** Validate the project root once at plugin activation. */
export function assertProjectRoot(cfg) {
    if (!isDirectory(cfg.projectRoot))
        throw new Error(`projectRoot is not a directory: ${cfg.projectRoot}`);
    if (!existsSync(path.join(cfg.projectRoot, 'AGENTS.md'))) {
        throw new Error(`projectRoot does not look like the 纹脉华章 workspace (AGENTS.md missing): ${cfg.projectRoot}`);
    }
}
/** Absolute, lexically normalised path for artifacts (no existence check). */
export function absolutePath(p) {
    return path.resolve(p);
}
