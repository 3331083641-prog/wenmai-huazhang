import type { PluginContext, PluginConfig } from './lib/sdk.js';
export declare const name = "wenmai-3d-reconstruction";
/** Cordis service injection: tools must exist before registration. */
export declare const inject: string[];
/**
 * Register every wenmai tool on the host registry.
 *
 * @param ctx - Cordis context carrying `tools`.
 * @param config - plain JSON config from the profile patch.
 * @returns a disposer that unregisters exactly the tools this plugin added.
 */
export declare function apply(ctx: PluginContext, config?: PluginConfig): () => void;
