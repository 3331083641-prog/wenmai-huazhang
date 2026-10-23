export interface LocalResultInput {
    task: string;
    artifacts?: Array<{
        kind: string;
        path: string;
    }>;
    checks?: Array<Record<string, unknown>>;
    warnings?: string[];
    notes?: string;
    projectRoot: string;
    [key: string]: unknown;
}
/** Shape a Node-side computation exactly like a Blender task result. */
export declare function makeLocalResult(input: LocalResultInput): Record<string, unknown>;
/** Recursively remove `undefined` members so the value stays lossless JSON. */
export declare function pruneUndefined<T>(value: T): T;
/** Write a JSON artifact and return its path. */
export declare function writeJsonArtifact(filePath: string, value: unknown): string;
/** Write a Markdown artifact and return its path. */
export declare function writeMarkdownArtifact(filePath: string, markdown: string): string;
