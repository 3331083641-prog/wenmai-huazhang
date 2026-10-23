function compileValue(spec) {
    const out = { type: spec.type };
    if (spec.description)
        out.description = spec.description;
    if (spec.enum)
        out.enum = spec.enum;
    if (spec.default !== undefined)
        out.default = spec.default;
    if (spec.minimum !== undefined)
        out.minimum = spec.minimum;
    if (spec.maximum !== undefined)
        out.maximum = spec.maximum;
    if (spec.minItems !== undefined)
        out.minItems = spec.minItems;
    if (spec.maxItems !== undefined)
        out.maxItems = spec.maxItems;
    if (spec.type === 'array')
        out.items = spec.items ? compileValue(spec.items) : { type: 'string' };
    if (spec.type === 'object') {
        out.properties = spec.properties ? compileProperties(spec.properties).properties : {};
        const required = spec.properties ? compileProperties(spec.properties).required : [];
        if (required.length > 0)
            out.required = required;
        out.additionalProperties = spec.additionalProperties ?? true;
    }
    return out;
}
function compileProperties(specs) {
    const properties = {};
    const required = [];
    for (const [key, spec] of Object.entries(specs)) {
        properties[key] = compileValue(spec);
        if (spec.required)
            required.push(key);
    }
    return { properties, required };
}
/** Compile a parameter map into the object-rooted schema the registry wants. */
export function compileParams(specs) {
    const { properties, required } = compileProperties(specs);
    const schema = { type: 'object', properties, additionalProperties: false };
    if (required.length > 0)
        schema.required = required;
    return schema;
}
export function describeParams(specs) {
    const parts = [];
    for (const [key, spec] of Object.entries(specs)) {
        const flag = spec.required ? ' (required)' : ' (optional)';
        const enumText = spec.enum ? ` one of ${spec.enum.map((v) => JSON.stringify(v)).join(' | ')}` : '';
        parts.push(`${key}: ${spec.type}${flag}${enumText}`);
    }
    return parts.join('; ');
}
/** Human-readable, bounded summary of a structured tool value. */
export function renderValue(title, value) {
    const lines = [title];
    if (value && typeof value === 'object' && !Array.isArray(value)) {
        const record = value;
        if (record.ok === false) {
            const err = record.error;
            lines.push(`STATUS: failed${err?.message ? ` — ${err.message}` : ''}`);
        }
        else {
            lines.push('STATUS: ok');
        }
        const artifacts = record.artifacts;
        if (Array.isArray(artifacts) && artifacts.length > 0) {
            lines.push('ARTIFACTS:');
            for (const item of artifacts.slice(0, 24)) {
                const a = item;
                lines.push(`  - [${String(a.kind ?? 'file')}] ${String(a.relativePath ?? a.path ?? '')} (${String(a.bytes ?? '?')} bytes)`);
            }
            if (artifacts.length > 24)
                lines.push(`  … ${artifacts.length - 24} more`);
        }
        const metrics = record.metrics;
        if (metrics && typeof metrics === 'object') {
            const text = JSON.stringify(metrics);
            lines.push(`METRICS: ${text.length > 1600 ? text.slice(0, 1600) + '…' : text}`);
        }
        const checks = record.checks;
        if (Array.isArray(checks) && checks.length > 0) {
            const counts = {};
            for (const item of checks) {
                const status = String(item.status ?? 'unknown');
                counts[status] = (counts[status] ?? 0) + 1;
            }
            lines.push(`CHECKS: ${Object.entries(counts).map(([k, v]) => `${k}=${v}`).join(', ')}`);
            for (const item of checks) {
                const c = item;
                if (c.status === 'fail' || c.status === 'warn') {
                    lines.push(`  - ${String(c.status).toUpperCase()} ${String(c.id)}: ${String(c.detail ?? '')}`);
                }
            }
        }
        const warnings = record.warnings;
        if (Array.isArray(warnings) && warnings.length > 0) {
            lines.push('WARNINGS:');
            for (const w of warnings.slice(0, 12))
                lines.push(`  - ${String(w)}`);
        }
        const notes = record.notes;
        if (typeof notes === 'string' && notes.trim()) {
            lines.push(`NOTES: ${notes.length > 1200 ? notes.slice(0, 1200) + '…' : notes}`);
        }
        const logPath = record.logPath;
        if (typeof logPath === 'string')
            lines.push(`LOG: ${logPath}`);
    }
    else {
        const text = JSON.stringify(value);
        lines.push(text.length > 3000 ? text.slice(0, 3000) + '…' : text);
    }
    return [{ type: 'text', text: lines.join('\n') }];
}
/**
 * Build a registry-ready tool. Argument validation is performed by the host
 * registry using the compiled schema; `execute` additionally re-validates the
 * few cross-field constraints the schema cannot express.
 */
export function defineBankTool(options) {
    const parameters = compileParams(options.parameters);
    const outputSchema = options.outputSchema ?? {
        type: 'object',
        additionalProperties: true,
        properties: {
            ok: { type: 'boolean' },
            task: { type: 'string' },
            artifacts: { type: 'array', items: { type: 'object', additionalProperties: true } },
        },
        required: ['ok'],
    };
    const title = options.renderTitle ?? options.name;
    const tool = {
        name: options.name,
        description: `${options.description}\n\nPARAMETERS: ${describeParams(options.parameters)}`,
        parameters,
        output: {
            schema: outputSchema,
            render: (_args, value) => renderValue(title, value),
        },
        execute: async (args, exec) => options.execute(args, exec),
        presentCall: (args) => ({ card: 'generic', title, kind: 'other', rawInput: args }),
        isConcurrencySafe: () => options.isConcurrencySafe === true,
    };
    if (options.timeoutMs !== undefined)
        tool.timeoutMs = options.timeoutMs;
    return tool;
}
