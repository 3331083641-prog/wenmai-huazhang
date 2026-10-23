/** Helpers for tools that compute in Node instead of driving Blender. */
import { mkdirSync, statSync, writeFileSync } from 'node:fs';
import path from 'node:path';
/** Shape a Node-side computation exactly like a Blender task result. */
export function makeLocalResult(input) {
    const { task, artifacts = [], checks = [], warnings = [], notes = '', projectRoot, ...rest } = input;
    const shapedArtifacts = artifacts.map((artifact) => {
        let bytes = 0;
        let exists = false;
        try {
            exists = statSync(artifact.path).isFile();
            if (exists)
                bytes = statSync(artifact.path).size;
        }
        catch {
            exists = false;
        }
        const relative = path.relative(projectRoot, artifact.path).replace(/\\/g, '/');
        return { kind: artifact.kind, path: artifact.path, bytes, exists, relativePath: relative };
    });
    return pruneUndefined({
        ok: true,
        task,
        jobId: 'local-' + Date.now().toString(36),
        durationMs: 0,
        artifacts: shapedArtifacts,
        checks,
        warnings,
        notes,
        logPath: '',
        ...rest,
    });
}
/** Recursively remove `undefined` members so the value stays lossless JSON. */
export function pruneUndefined(value) {
    if (Array.isArray(value)) {
        return value.filter((item) => item !== undefined).map((item) => pruneUndefined(item));
    }
    if (value && typeof value === 'object') {
        const out = {};
        for (const [key, item] of Object.entries(value)) {
            if (item === undefined)
                continue;
            out[key] = pruneUndefined(item);
        }
        return out;
    }
    return value;
}
/** Write a JSON artifact and return its path. */
export function writeJsonArtifact(filePath, value) {
    mkdirSync(path.dirname(filePath), { recursive: true });
    writeFileSync(filePath, JSON.stringify(value, null, 2), 'utf8');
    return filePath;
}
/** Write a Markdown artifact and return its path. */
export function writeMarkdownArtifact(filePath, markdown) {
    mkdirSync(path.dirname(filePath), { recursive: true });
    writeFileSync(filePath, markdown, 'utf8');
    return filePath;
}
