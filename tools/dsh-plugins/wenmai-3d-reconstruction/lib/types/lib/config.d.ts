import type { PluginConfig } from './sdk.js';
export declare const DEFAULT_PROJECT_ROOT = "D:\\wenmai-huazhang";
export declare const DEFAULT_BLENDER_EXE = "D:\\Codex\\blender-5.2.2\\blender-5.2.2-windows-x64\\blender.exe";
export interface ResolvedConfig {
    projectRoot: string;
    blenderExe: string;
    timeoutMs: number;
    workRoot: string;
    referencesDir: string;
    baseBlend: string;
    jobsDir: string;
    sceneDir: string;
    rendersDir: string;
    reportsDir: string;
    allowProjectWrites: boolean;
}
/** Resolve plugin config into absolute paths, filling documented defaults. */
export declare function resolveConfig(config: PluginConfig | undefined): ResolvedConfig;
/** Thrown by path validation; surfaced as a structured tool error. */
export declare class PathViolation extends Error {
    constructor(message: string);
}
/**
 * Resolve a user/model supplied path and require it to stay inside the project
 * root. Relative paths resolve against the project root.
 */
export declare function resolveInsideProject(cfg: ResolvedConfig, input: string, label?: string): string;
/** Resolve an existing input file inside the project root. */
export declare function requireProjectFile(cfg: ResolvedConfig, input: string, label?: string): string;
/** Resolve an output directory inside the project root, creating it later. */
export declare function resolveOutputDir(cfg: ResolvedConfig, input: string | undefined, fallback: string): string;
/** Validate the configured Blender executable (allowed outside the root). */
export declare function assertBlender(cfg: ResolvedConfig): string;
/** Validate the project root once at plugin activation. */
export declare function assertProjectRoot(cfg: ResolvedConfig): void;
/** Absolute, lexically normalised path for artifacts (no existence check). */
export declare function absolutePath(p: string): string;
