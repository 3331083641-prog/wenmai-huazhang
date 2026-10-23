import type { JsonValue } from './sdk.js';
export interface ObservationComponent {
    id: string;
    part: 'base' | 'roof' | 'timber' | 'wall' | 'floor' | 'stair' | 'railing' | 'interior' | 'prop' | 'frame';
    floor?: number;
    shape?: string;
    size?: [number, number, number];
    position?: [number, number, number];
    confidence?: number;
    sourceImage?: string;
    notes?: string;
    [key: string]: unknown;
}
export interface Observations {
    sourceImages?: string[];
    envelope?: Record<string, number>;
    components?: ObservationComponent[];
    constraints?: string[];
    unknowns?: string[];
    contradictions?: Array<Record<string, unknown>>;
    [key: string]: unknown;
}
export interface SceneSpec {
    schemaVersion: number;
    generatedBy: string;
    generatedAt: string;
    units: 'metre';
    up: 'Z';
    origin: string;
    coordinateContract: Record<string, string>;
    envelope: Record<string, number>;
    components: ObservationComponent[];
    constraints: string[];
    contradictions: Array<Record<string, unknown>>;
    unknowns: string[];
    evidence: Array<{
        image: string;
        usedFor: string;
    }>;
    measurementSummary?: Record<string, JsonValue>;
}
interface MeasurementsFile {
    images?: Array<Record<string, unknown>>;
    [key: string]: unknown;
}
/** Read measured band ratios from the analyser output (tolerant of layout). */
export declare function measurementSummary(measurements: MeasurementsFile | null): Record<string, JsonValue>;
export interface BuildSpecInput {
    observations: Observations;
    measurements: MeasurementsFile | null;
    measurementsPath?: string;
    projectRoot: string;
    outPath: string;
}
export declare function buildSceneSpec(input: BuildSpecInput): {
    spec: SceneSpec;
    specPath: string;
    validation: Record<string, JsonValue>;
    contradictions: Array<Record<string, unknown>>;
    unknowns: string[];
};
export declare function readJsonFile(filePath: string): unknown;
export {};
