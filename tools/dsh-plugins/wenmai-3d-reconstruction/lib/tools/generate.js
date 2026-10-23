/**
 * Module B — parametric architectural generator tools.
 *
 * Each generator replaces only its own `wm_part` group, so the roof can be
 * iterated without rebuilding the hall, the corridor without rebuilding the
 * diorama, and so on.
 */
import { existsSync } from 'node:fs';
import path from 'node:path';
import { requireProjectFile, resolveInsideProject } from '../lib/config.js';
import { runBlenderTask } from '../lib/blender.js';
import { defineBankTool } from '../lib/tool.js';
const NUMERIC_KEYS = [
    'footprintX', 'footprintY', 'eaveZ', 'ridgeZ', 'overhang', 'cornerLift', 'slopePower', 'ridgeHalf',
    'tileRows', 'tileCover', 'tileSegments', 'tileThickness', 'tileGap',
    'baysX', 'baysY', 'columnRadius', 'f1H', 'f2H', 'dougongLevels', 'rafterSpacing',
    'voidX', 'voidY', 'corridorWidth', 'railingHeight', 'stairWidth', 'stairRisers',
    'baseSize', 'plinthHeight', 'width', 'height', 'depth',
    'mainEaveZ', 'mainEaveFactor', 'skirtInset', 'spacing',
];
const BOOLEAN_KEYS = [
    'ridgeOrnament', 'displayWalls', 'lanterns', 'frieze', 'medallion', 'paving', 'fromProjectModel',
    'overwrite', 'draco', 'yUp',
];
// Path-like arguments (baseBlend/outBlend/blend/out/copyTo) are resolved by the
// Node side and travel in the job CONTEXT; they must never leak into `params`,
// or Blender would resolve them relative to its own working directory.
const STRING_KEYS = ['style', 'detail', 'ceilingStyle'];
function pickParams(cfg, args) {
    const params = {};
    for (const key of STRING_KEYS) {
        const value = args[key];
        if (typeof value === 'string' && value.trim() !== '')
            params[key] = value;
    }
    for (const key of NUMERIC_KEYS) {
        const value = args[key];
        if (typeof value === 'number' && Number.isFinite(value))
            params[key] = value;
    }
    for (const key of BOOLEAN_KEYS) {
        const value = args[key];
        if (typeof value === 'boolean')
            params[key] = value;
    }
    if (args.props && typeof args.props === 'object' && !Array.isArray(args.props))
        params.props = args.props;
    if (args.stair && typeof args.stair === 'object' && !Array.isArray(args.stair))
        params.stair = args.stair;
    void cfg;
    return params;
}
/** Decide which blend a generator continues from, and where it saves. */
export function resolveSceneTargets(cfg, args) {
    const workScene = path.join(cfg.sceneDir, 'wenmai_scene.blend');
    const explicitBase = typeof args.baseBlend === 'string' && args.baseBlend.trim() !== '';
    let baseBlend = null;
    if (explicitBase) {
        const raw = args.baseBlend;
        if (raw === 'none' || raw === 'new')
            baseBlend = null;
        else if (raw === 'project' || raw === 'v5')
            baseBlend = cfg.baseBlend;
        else
            baseBlend = requireProjectFile(cfg, raw, 'baseBlend');
    }
    else if (args.fromProjectModel === true) {
        baseBlend = requireProjectFile(cfg, cfg.baseBlend, 'project model');
    }
    else if (existsSync(workScene)) {
        baseBlend = workScene;
    }
    else if (existsSync(cfg.baseBlend) && args.fromProjectModel === undefined) {
        baseBlend = null;
    }
    const explicitOut = typeof args.outBlend === 'string' && args.outBlend.trim() !== '';
    let outBlend = explicitOut ? resolveInsideProject(cfg, args.outBlend, 'outBlend') : workScene;
    if (baseBlend && path.resolve(baseBlend) === path.resolve(outBlend)) {
        // In-place regeneration of our own work scene is the intended workflow; only
        // the read-only project model is protected.
        if (path.resolve(outBlend) === path.resolve(cfg.baseBlend)) {
            throw new Error('refusing to overwrite the read-only project model; pass a different outBlend');
        }
    }
    return { baseBlend, outBlend, explicitBase };
}
function runOptions(cfg, args) {
    const { baseBlend, outBlend } = resolveSceneTargets(cfg, args);
    return { baseBlend, outBlend };
}
export function generateTools(cfg) {
    const commonBlendParams = {
        baseBlend: {
            type: 'string',
            description: 'Blend to continue from: a project path, "project" for the v5 gallery model, "new" for an empty scene. ' +
                'Default: the plugin work scene when it exists, otherwise a new scene.',
        },
        outBlend: { type: 'string', description: 'Output .blend (default outputs/wenmai-3d/scene/wenmai_scene.blend)' },
        fromProjectModel: { type: 'boolean', description: 'Start from assets/gallery3d/blender/wenmai_gallery_v5.blend' },
        overwrite: { type: 'boolean', description: 'Allow saving over an existing outBlend (default true for the work scene)' },
    };
    const roof = defineBankTool({
        name: 'wm_generate_roof',
        description: 'Generate (or regenerate) the Chinese roof: concave hip slopes, parallel tile courses down each slope (never radial), ' +
            'eave tiles (瓦当/滴水), main + hip ridges with chiwen, rafters and a dougong band. Replaces only wm_part="roof" objects.',
        parameters: {
            ...commonBlendParams,
            style: { type: 'string', enum: ['hip', 'xieshan', 'gable', 'double-eave'], description: 'Roof form (default hip)' },
            footprintX: { type: 'number', description: 'Hall width X in metres (default 8.4)' },
            footprintY: { type: 'number', description: 'Hall depth Y in metres (default 7.5)' },
            eaveZ: { type: 'number', description: 'Eave height (default 6.15)' },
            ridgeZ: { type: 'number', description: 'Ridge height (default 11.3)' },
            overhang: { type: 'number', description: 'Eave projection beyond the wall plane (default 1.55)' },
            cornerLift: { type: 'number', description: 'Corner up-turn (default 0.55)' },
            slopePower: { type: 'number', description: 'Slope concavity, >1 = steeper at the ridge (default 1.75)' },
            ridgeHalf: { type: 'number', description: 'Half length of the main ridge (default 1.35)' },
            tileRows: { type: 'integer', description: 'Tile courses per slope (default 28)' },
            tileCover: { type: 'number', description: 'Course width in metres (default 1.35 / rows)' },
            tileSegments: { type: 'integer', description: 'Segments along the slope (default 26)' },
            tileThickness: { type: 'number', description: 'Tile thickness (default 0.045)' },
            ridgeOrnament: { type: 'boolean', description: 'Add chiwen/ridge ornaments (default true)' },
            detail: { type: 'string', enum: ['low', 'medium', 'high'], description: 'Geometry budget (default medium)' },
        },
        renderTitle: 'Roof generated',
        execute: async (raw, exec) => {
            const args = raw;
            const options = runOptions(cfg, args);
            const result = await runBlenderTask(cfg, 'generate_roof', pickParams(cfg, args), { ...options, signal: exec.signal });
            return result;
        },
    });
    const timber = defineBankTool({
        name: 'wm_generate_timber',
        description: 'Generate the timber frame: column grid, main/secondary beams, purlins, rafters, dougong blocks and connection nodes. ' +
            'Replaces only wm_part="timber" objects.',
        parameters: {
            ...commonBlendParams,
            baysX: { type: 'integer', description: 'Column bays along X (default 3)' },
            baysY: { type: 'integer', description: 'Column bays along Y (default 3)' },
            columnRadius: { type: 'number', description: 'Column radius in metres (default 0.16)' },
            f1H: { type: 'number', description: 'Ground storey clear height (default 3.35)' },
            f2H: { type: 'number', description: 'Upper storey clear height (default 2.95)' },
            dougongLevels: { type: 'integer', description: 'Bracket-set tiers under the eave (default 2)' },
            rafterSpacing: { type: 'number', description: 'Rafter spacing in metres (default 0.32)' },
            detail: { type: 'string', enum: ['low', 'medium', 'high'], description: 'Geometry budget (default medium)' },
        },
        renderTitle: 'Timber frame generated',
        execute: async (raw, exec) => {
            const args = raw;
            const options = runOptions(cfg, args);
            const result = await runBlenderTask(cfg, 'generate_timber', pickParams(cfg, args), { ...options, signal: exec.signal });
            return result;
        },
    });
    const interior = defineBankTool({
        name: 'wm_generate_interior',
        description: 'Generate the two-storey interior: floor slabs, central void, the open second-floor corridor (railing, lattice, carved ' +
            'fascia), a real stair connecting both floors, display walls, doors/windows, showcases, ceiling and lanterns. ' +
            'Preserves the 15 FRAME_F1_*/FRAME_F2_* anchors. Replaces only wm_part="interior" objects.',
        parameters: {
            ...commonBlendParams,
            voidX: { type: 'number', description: 'Central void width X (default 5.4)' },
            voidY: { type: 'number', description: 'Central void depth Y (default 4.6)' },
            corridorWidth: { type: 'number', description: '2F corridor width (default 1.9)' },
            railingHeight: { type: 'number', description: '2F railing height (default 1.05)' },
            stairWidth: { type: 'number', description: 'Stair width (default 1.2)' },
            stairRisers: { type: 'integer', description: 'Number of stair risers (default 18)' },
            ceilingStyle: { type: 'string', enum: ['coffered', 'beams'], description: 'Ceiling treatment (default coffered)' },
            displayWalls: { type: 'boolean', description: 'Build display walls for the frames (default true)' },
            lanterns: { type: 'boolean', description: 'Hang lanterns (default true)' },
            detail: { type: 'string', enum: ['low', 'medium', 'high'], description: 'Geometry budget (default medium)' },
        },
        renderTitle: 'Interior generated',
        execute: async (raw, exec) => {
            const args = raw;
            const options = runOptions(cfg, args);
            const result = await runBlenderTask(cfg, 'generate_interior', pickParams(cfg, args), { ...options, signal: exec.signal });
            return result;
        },
    });
    const diorama = defineBankTool({
        name: 'wm_generate_diorama',
        description: 'Generate the miniature street-corner diorama: 16 m plinth (dark foot, meander frieze band, medallion), stone paving, ' +
            'steps, trees, bamboo, planters, lanterns, stone lamps and banner poles. Replaces only wm_part="diorama" objects.',
        parameters: {
            ...commonBlendParams,
            baseSize: { type: 'number', description: 'Square plinth side in metres (default 16)' },
            plinthHeight: { type: 'number', description: 'Plinth height below z=0 (default 0.65)' },
            frieze: { type: 'boolean', description: 'Carved frieze band (default true)' },
            medallion: { type: 'boolean', description: 'Central lotus medallion (default true)' },
            paving: { type: 'boolean', description: 'Stone paving and steps (default true)' },
            props: { type: 'object', additionalProperties: true, description: '{trees,bamboo,planters,lanterns,stoneLamps,banners} booleans' },
            detail: { type: 'string', enum: ['low', 'medium', 'high'], description: 'Geometry budget (default medium)' },
        },
        renderTitle: 'Diorama generated',
        execute: async (raw, exec) => {
            const args = raw;
            const options = runOptions(cfg, args);
            const result = await runBlenderTask(cfg, 'generate_diorama', pickParams(cfg, args), { ...options, signal: exec.signal });
            return result;
        },
    });
    const exportGlb = defineBankTool({
        name: 'wm_export_glb',
        description: 'Export the work scene (or a given .blend) to GLB with Y-up conversion for Three.js, then re-open the GLB in Blender to ' +
            'count meshes, triangles, materials and textures. Optionally copies the GLB to a path inside the project.',
        parameters: {
            blend: {
                type: 'string',
                description: 'Blend to export (default outputs/wenmai-3d/scene/wenmai_scene.blend)',
            },
            out: { type: 'string', description: 'GLB output path (default outputs/wenmai-3d/scene/wenmai_scene.glb)' },
            copyTo: {
                type: 'string',
                description: 'Optional copy target inside the project, e.g. frontend/public/models/wenmai_gallery_v5_wm.glb',
            },
            yUp: { type: 'boolean', description: 'Convert Z-up to Y-up for Three.js (default true)' },
            draco: { type: 'boolean', description: 'Reserved; Draco compression is not enabled by default' },
        },
        renderTitle: 'GLB exported',
        execute: async (raw, exec) => {
            const args = raw;
            const explicitBlend = typeof args.blend === 'string' && args.blend.trim() !== '';
            const blend = explicitBlend
                ? requireProjectFile(cfg, args.blend, 'blend')
                : path.join(cfg.sceneDir, 'wenmai_scene.blend');
            if (!existsSync(blend))
                throw new Error(`blend not found: ${blend} (generate a part first)`);
            const explicitOut = typeof args.out === 'string' && args.out.trim() !== '';
            const out = explicitOut
                ? resolveInsideProject(cfg, args.out, 'out')
                : path.join(cfg.sceneDir, 'wenmai_scene.glb');
            const copyTo = typeof args.copyTo === 'string' && args.copyTo.trim() !== ''
                ? resolveInsideProject(cfg, args.copyTo, 'copyTo')
                : null;
            const result = await runBlenderTask(cfg, 'export_glb', { blend, out, copyTo, yUp: args.yUp !== false }, { baseBlend: blend, outBlend: blend, signal: exec.signal });
            return result;
        },
    });
    return [roof, timber, interior, diorama, exportGlb];
}
