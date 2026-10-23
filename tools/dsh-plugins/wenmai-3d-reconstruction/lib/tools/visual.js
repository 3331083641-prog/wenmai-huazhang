/**
 * Module C — visual matching tools.
 *
 *   wm_capture_views              real EEVEE renders from fixed viewpoints
 *   wm_compare_reference          reference vs render: side-by-side, overlay, contour, metrics
 *   wm_generate_diff_report       rank differences into a Markdown/JSON report (Node)
 *   wm_propose_geometry_changes   map measured deltas onto generator parameters
 */
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { requireProjectFile, resolveInsideProject, resolveOutputDir } from '../lib/config.js';
import { runBlenderTask } from '../lib/blender.js';
import { defineBankTool } from '../lib/tool.js';
import { makeLocalResult, writeJsonArtifact, writeMarkdownArtifact } from '../lib/result.js';
const STANDARD_VIEWS = [
    'front34', 'front', 'left', 'right', 'back', 'top', 'base_low',
    'floor1', 'floor2', 'ceiling', 'eave', 'corner',
];
function stringArg(args, key) {
    const value = args[key];
    if (value === undefined || value === null)
        return undefined;
    if (typeof value !== 'string')
        throw new Error(`parameter "${key}" must be a string`);
    return value;
}
function numberArg(args, key) {
    const value = args[key];
    if (value === undefined || value === null)
        return undefined;
    if (typeof value !== 'number' || !Number.isFinite(value))
        throw new Error(`parameter "${key}" must be a number`);
    return value;
}
function defaultBlend(cfg, args, required = true) {
    const explicit = stringArg(args, 'blend');
    if (explicit)
        return requireProjectFile(cfg, explicit, 'blend');
    const workScene = path.join(cfg.sceneDir, 'wenmai_scene.blend');
    if (existsSync(workScene))
        return workScene;
    if (existsSync(cfg.baseBlend))
        return cfg.baseBlend;
    if (required)
        throw new Error(`no blend available; generate a part first or pass blend`);
    return workScene;
}
function severityScore(comparison) {
    const metrics = comparison.metrics;
    const iou = typeof metrics?.silhouetteIoU === 'number' ? metrics.silhouetteIoU : undefined;
    const colorDelta = typeof metrics?.regionColorDelta === 'number' ? metrics.regionColorDelta : undefined;
    const contour = typeof metrics?.bandEdgeError === 'number' ? metrics.bandEdgeError : undefined;
    let score = 0;
    if (iou !== undefined)
        score += (1 - iou) * 60;
    if (colorDelta !== undefined)
        score += Math.min(40, colorDelta / 2);
    if (contour !== undefined)
        score += Math.min(40, contour * 100);
    return Math.round(score * 10) / 10;
}
export function visualTools(cfg) {
    const capture = defineBankTool({
        name: 'wm_capture_views',
        description: 'Render real EEVEE screenshots of the model from fixed viewpoints (front34, front, left, right, back, top, base_low, ' +
            'floor1, floor2, ceiling, eave, corner) with a reference-matched lighting rig. Returns real PNG paths and camera data.',
        parameters: {
            blend: { type: 'string', description: 'Blend to render (default: plugin work scene, else the v5 model)' },
            views: {
                type: 'array',
                items: { type: 'string', enum: [...STANDARD_VIEWS] },
                description: 'Views to render (default: front34, front, top, eave)',
            },
            camerasPath: { type: 'string', description: 'Optional camera JSON to render from (same shape as wm_match_camera output)' },
            width: { type: 'integer', minimum: 320, maximum: 3840, description: 'Image width (default 1200)' },
            height: { type: 'integer', minimum: 240, maximum: 2160, description: 'Image height (default 900)' },
            samples: { type: 'integer', minimum: 8, maximum: 256, description: 'EEVEE samples (default 48)' },
            outDir: { type: 'string', description: 'Output directory (default outputs/wenmai-3d/renders/<job>)' },
        },
        renderTitle: 'Views captured',
        execute: async (raw, exec) => {
            const args = raw;
            const blend = defaultBlend(cfg, args);
            const viewsInput = Array.isArray(args.views) ? args.views : ['front34', 'front', 'top', 'eave'];
            const views = viewsInput.filter((view) => typeof view === 'string');
            if (views.length === 0)
                throw new Error('views must contain at least one view name');
            const unknown = views.filter((view) => !STANDARD_VIEWS.includes(view));
            if (unknown.length > 0)
                throw new Error(`unknown views: ${unknown.join(', ')}`);
            const outDir = resolveOutputDir(cfg, stringArg(args, 'outDir'), path.join(cfg.rendersDir, 'capture'));
            const camerasPath = stringArg(args, 'camerasPath')
                ? requireProjectFile(cfg, stringArg(args, 'camerasPath'), 'camerasPath')
                : null;
            const result = await runBlenderTask(cfg, 'capture_views', {
                blend,
                views,
                camerasPath,
                width: numberArg(args, 'width') ?? 1200,
                height: numberArg(args, 'height') ?? 900,
                samples: numberArg(args, 'samples') ?? 48,
                outDir,
            }, { baseBlend: blend, outBlend: blend, signal: exec.signal });
            return result;
        },
    });
    const compare = defineBankTool({
        name: 'wm_compare_reference',
        description: 'Align a reference image with a real render and produce side-by-side, overlay and contour PNGs plus numeric metrics ' +
            '(silhouette IoU, centroid/scale offset, band edge error, Lab colour delta, detail ratio). Never invents a fidelity score.',
        parameters: {
            reference: { type: 'string', required: true, description: 'Reference image path inside the project' },
            render: { type: 'string', required: true, description: 'Render PNG path inside the project' },
            outDir: { type: 'string', description: 'Output directory (default outputs/wenmai-3d/reports/comparisons)' },
            align: { type: 'string', enum: ['auto', 'none'], description: 'Foreground-bbox alignment (default auto)' },
            cameraPath: { type: 'string', description: 'Optional solved camera JSON used for the render' },
        },
        renderTitle: 'Reference comparison',
        execute: async (raw, exec) => {
            const args = raw;
            const reference = requireProjectFile(cfg, stringArg(args, 'reference') ?? '', 'reference');
            const render = requireProjectFile(cfg, stringArg(args, 'render') ?? '', 'render');
            const outDir = resolveOutputDir(cfg, stringArg(args, 'outDir'), path.join(cfg.reportsDir, 'comparisons'));
            const cameraPath = stringArg(args, 'cameraPath')
                ? requireProjectFile(cfg, stringArg(args, 'cameraPath'), 'cameraPath')
                : null;
            const result = await runBlenderTask(cfg, 'compare_reference', {
                reference,
                render,
                outDir,
                outPath: path.join(outDir, `comparison_${path.basename(reference, path.extname(reference))}.json`),
                align: stringArg(args, 'align') ?? 'auto',
                cameraPath,
            }, { signal: exec.signal });
            return result;
        },
    });
    const diffReport = defineBankTool({
        name: 'wm_generate_diff_report',
        description: 'Rank the measured differences into a report: the five largest deviations, the evidence for each, and the model region ' +
            'they belong to. Accepts comparison result objects and/or comparison JSON paths.',
        parameters: {
            comparisons: {
                type: 'array',
                description: 'Comparison result objects returned by wm_compare_reference',
                items: { type: 'object', additionalProperties: true },
            },
            comparisonPaths: {
                type: 'array',
                items: { type: 'string' },
                description: 'Alternatively, paths to comparison JSON files',
            },
            outDir: { type: 'string', description: 'Report directory (default outputs/wenmai-3d/reports/diff)' },
            title: { type: 'string', description: 'Report title' },
        },
        renderTitle: 'Difference report',
        isConcurrencySafe: true,
        execute: async (raw) => {
            const args = raw;
            const inline = Array.isArray(args.comparisons) ? args.comparisons : [];
            const paths = Array.isArray(args.comparisonPaths) ? args.comparisonPaths : [];
            const loaded = [...inline];
            for (const p of paths) {
                const file = requireProjectFile(cfg, p, 'comparisonPaths[]');
                const parsed = JSON.parse(readFileSync(file, 'utf8'));
                loaded.push(parsed);
            }
            if (loaded.length === 0)
                throw new Error('provide comparisons or comparisonPaths');
            const outDir = resolveOutputDir(cfg, stringArg(args, 'outDir'), path.join(cfg.reportsDir, 'diff'));
            const title = stringArg(args, 'title') ?? '纹脉展馆 · 参考图对照差异报告';
            const ranked = loaded
                .map((comparison) => {
                const regions = Array.isArray(comparison.regions) ? comparison.regions : [];
                const weight = (region) => {
                    const raw = region.severity ?? region.delta ?? 0;
                    const value = Number(raw);
                    return Number.isFinite(value) ? value : 0;
                };
                const worst = [...regions].sort((a, b) => weight(b) - weight(a))[0];
                return {
                    reference: comparison.reference ?? comparison.image ?? null,
                    render: comparison.render ?? null,
                    score: severityScore(comparison),
                    metrics: comparison.metrics ?? null,
                    worstRegion: worst ?? null,
                };
            })
                .sort((a, b) => b.score - a.score);
            const top = ranked.slice(0, 5);
            const markdown = [
                `# ${title}`,
                '',
                `生成时间：${new Date().toISOString()}`,
                `对照数量：${loaded.length}`,
                '',
                '## 差异最大的五个位置',
                '',
                '| # | 参考图 | 综合偏差 | 最差区域 | 证据 |',
                '|---|---|---|---|---|',
                ...top.map((item, index) => {
                    const region = (item.worstRegion ?? {});
                    return `| ${index + 1} | ${String(item.reference ?? '')} | ${item.score} | ${String(region.name ?? region.region ?? '—')} | ${JSON.stringify(region).slice(0, 220)} |`;
                }),
                '',
                '## 每组指标',
                '',
                '```json',
                JSON.stringify(ranked, null, 2).slice(0, 12000),
                '```',
                '',
                '> 指标来自真实渲染与真实参考图的几何/色彩测量；未检查项不得视为通过。',
            ].join('\n');
            const reportPath = writeJsonArtifact(path.join(outDir, 'diff_report.json'), {
                generatedAt: new Date().toISOString(),
                title,
                ranked,
                topDifferences: top,
            });
            const markdownPath = writeMarkdownArtifact(path.join(outDir, 'diff_report.md'), markdown);
            return makeLocalResult({
                task: 'generate_diff_report',
                projectRoot: cfg.projectRoot,
                artifacts: [
                    { kind: 'json', path: reportPath },
                    { kind: 'markdown', path: markdownPath },
                ],
                checks: [
                    {
                        id: 'comparisons_loaded',
                        status: 'pass',
                        detail: `${loaded.length} comparison(s)`,
                    },
                ],
                notes: `Top ${top.length} deviations ranked by geometric + colour evidence.`,
                reportPath,
                markdownPath,
                topDifferences: top,
                markdown,
            });
        },
    });
    const propose = defineBankTool({
        name: 'wm_propose_geometry_changes',
        description: 'Turn measured differences into concrete, ordered parameter changes on the generator (e.g. overhang, cornerLift, ' +
            'slopePower, railingHeight), each with the evidence and expected visual effect. Writes a JSON + Markdown plan.',
        parameters: {
            comparisonPath: { type: 'string', description: 'comparison_*.json from wm_compare_reference' },
            reportPath: { type: 'string', description: 'Or diff_report.json from wm_generate_diff_report' },
            specPath: { type: 'string', description: 'Optional scene spec for component context' },
            outDir: { type: 'string', description: 'Output directory (default outputs/wenmai-3d/reports/changes)' },
        },
        renderTitle: 'Geometry change proposals',
        execute: async (raw, exec) => {
            const args = raw;
            const comparison = stringArg(args, 'comparisonPath')
                ? requireProjectFile(cfg, stringArg(args, 'comparisonPath'), 'comparisonPath')
                : null;
            const report = stringArg(args, 'reportPath')
                ? requireProjectFile(cfg, stringArg(args, 'reportPath'), 'reportPath')
                : null;
            if (!comparison && !report) {
                const fallback = path.join(cfg.reportsDir, 'comparisons');
                throw new Error(`provide comparisonPath or reportPath (comparison default directory: ${fallback})`);
            }
            const specPath = stringArg(args, 'specPath')
                ? requireProjectFile(cfg, stringArg(args, 'specPath'), 'specPath')
                : null;
            const outDir = resolveOutputDir(cfg, stringArg(args, 'outDir'), path.join(cfg.reportsDir, 'changes'));
            const result = await runBlenderTask(cfg, 'propose_geometry_changes', { comparisonPath: comparison, reportPath: report, specPath, outDir }, { signal: exec.signal });
            return result;
        },
    });
    return [capture, compare, diffReport, propose];
}
/** Used by the e2e harness to know the supported fixed views. */
export const VISUAL_STANDARD_VIEWS = STANDARD_VIEWS;
export function asTaskResult(value) {
    return value;
}
/** Default comparison artifact expected after wm_compare_reference. */
export function defaultComparisonPath(cfg) {
    return path.join(cfg.reportsDir, 'comparisons');
}
export function ensureInside(cfg, candidate) {
    return resolveInsideProject(cfg, candidate, 'path');
}
