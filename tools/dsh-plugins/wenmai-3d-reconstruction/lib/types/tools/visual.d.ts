import type { JsonValue, ToolDefinition } from '../lib/sdk.js';
import type { ResolvedConfig } from '../lib/config.js';
import { type TaskResult } from '../lib/blender.js';
export declare function visualTools(cfg: ResolvedConfig): ToolDefinition[];
/** Used by the e2e harness to know the supported fixed views. */
export declare const VISUAL_STANDARD_VIEWS: readonly ["front34", "front", "left", "right", "back", "top", "base_low", "floor1", "floor2", "ceiling", "eave", "corner"];
export declare function asTaskResult(value: JsonValue): TaskResult;
/** Default comparison artifact expected after wm_compare_reference. */
export declare function defaultComparisonPath(cfg: ResolvedConfig): string;
export declare function ensureInside(cfg: ResolvedConfig, candidate: string): string;
