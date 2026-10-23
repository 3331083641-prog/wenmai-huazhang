/**
 * Minimal host typings for the DSH 0.2.1-rc.2 Cordis plugin surface this
 * package uses.
 *
 * The plugin deliberately imports NOTHING from `@deepseek-ai/*` at runtime:
 * the profile it is installed into does not own a copy of the DSH runtime, and
 * a second copy of cordis/dsh-tools would be a real compatibility hazard. The
 * tool registry only needs plain `ToolDefinition` objects, so this file models
 * exactly that wire shape. Keep it in sync with `@deepseek-ai/dsh-tools`
 * (`defineTool` output) when the host version changes.
 */
export type JsonValue = null | boolean | number | string | JsonValue[] | {
    [key: string]: JsonValue;
};
/** Raw JSON Schema subset accepted by the DSH tool registry. */
export interface JsonSchema {
    type?: 'string' | 'number' | 'integer' | 'boolean' | 'null' | 'array' | 'object';
    description?: string;
    enum?: JsonValue[];
    const?: JsonValue;
    properties?: Record<string, JsonSchema>;
    required?: string[];
    additionalProperties?: boolean | JsonSchema;
    items?: JsonSchema;
    oneOf?: JsonSchema[];
    anyOf?: JsonSchema[];
    minimum?: number;
    maximum?: number;
    minItems?: number;
    maxItems?: number;
    default?: JsonValue;
    title?: string;
}
/** Content block handed back to the model for a tool result. */
export interface ToolContentBlock {
    type: 'text';
    text: string;
}
/** Execution context the registry passes to `execute`. */
export interface ToolExecution {
    /** Caller-owned cancellation signal; a tool body must observe it. */
    signal: AbortSignal;
    /** Owning agent (present for model-facing calls). */
    agent?: unknown;
    /** Correlation token (opaque). */
    callId?: string;
}
/** Registry-ready tool definition (the shape `defineTool()` produces). */
export interface ToolDefinition {
    name: string;
    description: string;
    /** Compiled parameter schema: an object-rooted raw JSON Schema. */
    parameters: JsonSchema;
    output: {
        schema: JsonSchema;
        render: (args: Record<string, JsonValue>, value: JsonValue) => ToolContentBlock[];
    };
    execute: (args: Record<string, JsonValue>, exec: ToolExecution) => Promise<JsonValue>;
    presentCall?: (args: Record<string, JsonValue>) => unknown;
    isConcurrencySafe?: (args: Record<string, JsonValue>) => boolean;
    timeoutMs?: number;
    deferLoading?: boolean;
}
export interface ToolRegistry {
    register(tool: ToolDefinition): () => void;
}
/** The slice of the Cordis context this plugin injects. */
export interface PluginContext {
    tools: ToolRegistry;
    logger?: (name?: string) => {
        info?: (...args: unknown[]) => void;
        warn?: (...args: unknown[]) => void;
        error?: (...args: unknown[]) => void;
    };
    get?: (name: string) => unknown;
    on?: (event: string, listener: (...args: unknown[]) => void) => () => void;
}
/** Plugin config as it arrives from `cordis.patch.yml` (plain JSON). */
export interface PluginConfig {
    /** Authorized project root; every generated/read path must stay inside it. */
    projectRoot?: string;
    /** Blender executable (absolute, outside the project root is allowed). */
    blenderExe?: string;
    /** Per-invocation Blender timeout. */
    timeoutMs?: number;
    /** Optional overrides for the artifact layout. */
    workRoot?: string;
    referencesDir?: string;
    baseBlend?: string;
    /** Hard enable switch for the destructive-ish generators. */
    allowProjectWrites?: boolean;
}
