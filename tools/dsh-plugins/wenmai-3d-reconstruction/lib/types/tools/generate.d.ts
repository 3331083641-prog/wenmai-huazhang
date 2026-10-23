import type { JsonValue, ToolDefinition } from '../lib/sdk.js';
import type { ResolvedConfig } from '../lib/config.js';
type Args = Record<string, JsonValue>;
/** Decide which blend a generator continues from, and where it saves. */
export declare function resolveSceneTargets(cfg: ResolvedConfig, args: Args): {
    baseBlend: string | null;
    outBlend: string;
    explicitBase: boolean;
};
export declare function generateTools(cfg: ResolvedConfig): ToolDefinition[];
export {};
