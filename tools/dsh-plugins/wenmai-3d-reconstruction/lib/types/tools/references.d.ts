import type { ToolDefinition } from '../lib/sdk.js';
import type { ResolvedConfig } from '../lib/config.js';
export declare function referenceTools(cfg: ResolvedConfig): ToolDefinition[];
/** Exported for the e2e harness: deterministic reference ids. */
export declare function referenceIds(count: number): string[];
/** Also exported so a spec writer can create a stub body without Blender. */
export declare function stubSpecPath(cfg: ResolvedConfig): string;
