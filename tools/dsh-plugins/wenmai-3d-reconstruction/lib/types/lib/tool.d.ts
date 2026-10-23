/**
 * Tool-definition factory for the DSH 0.2.1-rc.2 registry.
 *
 * We intentionally do not import `@deepseek-ai/dsh-tools`: the profile that
 * hosts this plugin does not own a copy of the DSH runtime, and importing a
 * second copy of the runtime (or its schemastery/zod closure) is the exact
 * compatibility hazard the project forbids. `defineTool` output is a plain
 * object with a compiled JSON Schema — this factory produces that identical
 * wire shape, and the registry validates arguments against it.
 */
import type { JsonSchema, JsonValue, ToolContentBlock, ToolDefinition, ToolExecution } from './sdk.js';
export interface ParamSpec {
    type: 'string' | 'number' | 'integer' | 'boolean' | 'array' | 'object';
    description?: string;
    required?: boolean;
    enum?: JsonValue[];
    default?: JsonValue;
    items?: ParamSpec;
    properties?: Record<string, ParamSpec>;
    additionalProperties?: boolean;
    minimum?: number;
    maximum?: number;
    maxItems?: number;
    minItems?: number;
}
/** Compile a parameter map into the object-rooted schema the registry wants. */
export declare function compileParams(specs: Record<string, ParamSpec>): JsonSchema;
export declare function describeParams(specs: Record<string, ParamSpec>): string;
/** Human-readable, bounded summary of a structured tool value. */
export declare function renderValue(title: string, value: JsonValue): ToolContentBlock[];
export interface BankToolOptions {
    name: string;
    description: string;
    parameters: Record<string, ParamSpec>;
    /** Loose output schema: the exact result shape is documented per tool. */
    outputSchema?: JsonSchema;
    renderTitle?: string;
    execute: (args: Record<string, JsonValue>, exec: ToolExecution) => Promise<JsonValue>;
    isConcurrencySafe?: boolean;
    timeoutMs?: number;
}
/**
 * Build a registry-ready tool. Argument validation is performed by the host
 * registry using the compiled schema; `execute` additionally re-validates the
 * few cross-field constraints the schema cannot express.
 */
export declare function defineBankTool(options: BankToolOptions): ToolDefinition;
