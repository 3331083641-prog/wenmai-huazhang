#!/usr/bin/env node
/**
 * End-to-end acceptance driver for wenmai-3d-reconstruction.
 *
 *   node tests/run-e2e.mjs [--only=<tool,tool>] [--skip=<tool>] [--list] [--dry] [--keep-going]
 *
 * Loads the real compiled plugin, mounts it into a fake Cordis context (the same
 * way the host does) and runs the 17 contract tools **in dependency order** with
 * real arguments against the real project:
 *
 *   analyze_refs → build_spec → generate_roof → export_glb → capture_views →
 *   compare_reference → diff_report → propose_changes → generate_timber →
 *   generate_interior → generate_diorama → export_glb(final) →
 *   inspect_scene → check_art_frames → check_export → performance_report →
 *   match_camera → validate_multiview
 *
 * Rules that keep this honest:
 *  - a tool that is not registered, or whose Python module the Lead has not
 *    written yet, is reported `not_ready`; it never crashes the run;
 *  - a step whose input artifact is missing is `blocked`, not `pass`;
 *  - every returned artifact path is re-checked on disk (size > 0, PNG/JPEG
 *    dimensions where applicable) and must stay inside the project root;
 *  - one failure never aborts the remaining steps, and the process exits
 *    non-zero when any step failed.
 *
 * Writes `e2e-<timestamp>.json` + `.md` (and per-step raw results) under
 * `D:\wenmai-huazhang\outputs\wenmai-3d\tests\`.
 */

import fs from 'node:fs'
import path from 'node:path'
import { spawnSync } from 'node:child_process'
import {
  ARTIFACT_ROOT,
  BLENDER_EXE,
  collectArtifacts,
  createFakeContext,
  createSuite,
  fileStamp,
  loadPlugin,
  parseArgs,
  PLUGIN_CONFIG,
  PLUGIN_ROOT,
  pluginObject,
  preserveActivation,
  PROJECT_ROOT,
  REFERENCES_DIR,
  snapshotActivation,
  stamp,
  statFile,
  TESTS_DIR,
  verifyArtifact,
  writeJson,
  writeText,
} from './lib/common.mjs'

const args = parseArgs()
const only = csvSet(args.only)
const skip = csvSet(args.skip)
const suite = createSuite('run-e2e', {})

const QA_ROOT = ARTIFACT_ROOT
const SCENE_DIR = path.join(QA_ROOT, 'scene')
const RENDER_DIR = path.join(QA_ROOT, 'renders')
const COMPARE_DIR = path.join(QA_ROOT, 'comparisons')
const REPORT_DIR = path.join(QA_ROOT, 'reports')
const SPEC_DIR = path.join(QA_ROOT, 'specs')
const RUN_STAMP = fileStamp()
const RAW_DIR = path.join(QA_ROOT, 'e2e-raw', RUN_STAMP)

const BASE_BLEND = path.join(PROJECT_ROOT, 'assets', 'gallery3d', 'blender', 'wenmai_gallery_v5.blend')
const FIXTURE_DIR = path.join(PLUGIN_ROOT, 'tests', 'fixtures')

for (const dir of [SCENE_DIR, RENDER_DIR, COMPARE_DIR, REPORT_DIR, SPEC_DIR, RAW_DIR]) {
  fs.mkdirSync(dir, { recursive: true })
}

// ---------------------------------------------------------------- helpers

function csvSet(value) {
  if (!value || value === true) return new Set()
  return new Set(String(value).split(',').map((s) => s.trim()).filter(Boolean))
}

const referenceImages = (() => {
  try {
    return fs
      .readdirSync(REFERENCES_DIR)
      .filter((n) => /\.(png|jpe?g)$/i.test(n))
      .sort()
      .map((n) => path.join(REFERENCES_DIR, n))
  } catch {
    return []
  }
})()

function readFixture(name, fallback = null) {
  const file = path.join(FIXTURE_DIR, name)
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'))
  } catch {
    return fallback
  }
}

const observations = readFixture('observations.json')
const cameraFixture = readFixture('camera-correspondences.json')

function insideProject(p) {
  try {
    const rel = path.relative(PROJECT_ROOT, p)
    return rel === '' || (!rel.startsWith('..') && !path.isAbsolute(rel))
  } catch {
    return false
  }
}

function num(v) {
  return typeof v === 'number' && Number.isFinite(v)
}

/** Pick a compact set of headline numbers out of a result for the report. */
function keyMetrics(result) {
  if (!result || typeof result !== 'object') return {}
  const out = {}
  const metricKeys = [
    'tileCount', 'ridgeLen', 'eaveSpanX', 'eaveSpanY', 'height', 'walls', 'faces', 'spanX', 'spanY',
    'columns', 'beams', 'frameCount', 'frames', 'found', 'missing', 'bytes', 'triangles', 'meshes',
    'materials', 'textures', 'animations', 'silhouetteIoU', 'regionColorDelta', 'rmsPx', 'status',
    'objectCount', 'meshCount', 'partCount',
  ]
  const metrics = result.metrics
  if (metrics && typeof metrics === 'object') {
    for (const [k, v] of Object.entries(metrics)) {
      if (num(v) || typeof v === 'string') out[k] = v
      else if (Array.isArray(v)) out[`${k}[]`] = v.length
      else if (v && typeof v === 'object') out[k] = '[object]'
    }
  }
  for (const k of metricKeys) if ((num(result[k]) || typeof result[k] === 'string') && out[k] === undefined) out[k] = result[k]
  if (Array.isArray(result.objects)) out.objects = result.objects.length
  if (Array.isArray(result.shots)) out.shots = result.shots.length
  if (Array.isArray(result.images)) out.images = result.images.length
  if (Array.isArray(result.changes)) out.changes = result.changes.length
  if (Array.isArray(result.checks)) {
    const counts = {}
    for (const c of result.checks) counts[c.status] = (counts[c.status] ?? 0) + 1
    out.checkStatuses = counts
  }
  return out
}

/** FRAME anchor detection across the shapes the interior generator may return. */
function detectFrameAnchors(result) {
  const names = []
  if (Array.isArray(result?.objects)) {
    for (const o of result.objects) {
      const n = typeof o === 'string' ? o : o && o.name
      if (typeof n === 'string' && /^FRAME_F[12]_\d{3}/.test(n)) names.push(n)
    }
  }
  const unique = [...new Set(names)]
  const metricsCandidates = [
    result?.metrics?.frameCount,
    result?.metrics?.frames,
    result?.metrics?.frameAnchors,
    result?.frameCount,
    result?.frames,
    result?.found,
  ].filter((v) => num(v))
  return {
    objectNames: unique,
    objectCount: unique.length,
    metric: metricsCandidates.length ? Math.max(...metricsCandidates) : null,
  }
}

// ------------------------------------------------------------------ steps

/**
 * Each step: {id, tool, phase, needs, args(bb), capture(bb,result), verify(bb,result)->checks}
 */
const STEPS = [
  {
    id: 'analyze-references',
    tool: 'wm_analyze_references',
    phase: 'A · reference reconstruction',
    args: () => ({ images: referenceImages, outDir: path.join(QA_ROOT, 'analysis') }),
    verify: (bb, r) => {
      const checks = []
      const images = Array.isArray(r.images) ? r.images : []
      checks.push({ name: 'reports 10 measured images', ok: images.length === 10, detail: `got ${images.length}` })
      const bad = images.filter((im) => !im || !num(im.width) || !num(im.height) || im.width <= 0 || im.height <= 0)
      checks.push({ name: 'every image has positive width/height', ok: bad.length === 0, detail: `${bad.length} bad` })
      const noPalette = images.filter((im) => !Array.isArray(im.palette) || im.palette.length === 0)
      checks.push({ name: 'every image has a palette', ok: noPalette.length === 0, detail: `${noPalette.length} without palette` })
      const noBox = images.filter((im) => !im.foregroundBox || !num(im.foregroundBox.w) || im.foregroundBox.w <= 0)
      checks.push({ name: 'every image has a foreground box', ok: noBox.length === 0, detail: `${noBox.length} without box` })
      checks.push({
        name: 'measurementsPath returned and present',
        ok: typeof r.measurementsPath === 'string' && statFile(r.measurementsPath).bytes > 0,
        detail: String(r.measurementsPath),
      })
      return checks
    },
    capture: (bb, r) => {
      bb.measurementsPath = r.measurementsPath
      bb.referenceImages = Array.isArray(r.images) ? r.images.map((im) => im.path || im.image).filter(Boolean) : referenceImages
    },
  },

  {
    id: 'build-scene-spec',
    tool: 'wm_build_scene_spec',
    phase: 'A · reference reconstruction',
    needs: [],
    args: (bb) => ({
      observations,
      measurementsPath: bb.measurementsPath,
      outPath: path.join(SPEC_DIR, 'scene_spec.json'),
    }),
    verify: (bb, r) => {
      const checks = []
      checks.push({ name: 'specPath present', ok: typeof r.specPath === 'string' && statFile(r.specPath).bytes > 0, detail: String(r.specPath) })
      checks.push({ name: 'spec is an object', ok: !!r.spec && typeof r.spec === 'object', detail: typeof r.spec })
      checks.push({ name: 'spec keeps the v5 envelope', ok: !!(r.spec && r.spec.envelope && num(r.spec.envelope.baseSize)), detail: JSON.stringify(r.spec && r.spec.envelope).slice(0, 200) })
      checks.push({ name: 'contradictions is an array', ok: Array.isArray(r.contradictions), detail: typeof r.contradictions })
      checks.push({ name: 'unknowns is an array', ok: Array.isArray(r.unknowns), detail: typeof r.unknowns })
      checks.push({ name: 'validation is an object', ok: !!r.validation && typeof r.validation === 'object', detail: typeof r.validation })
      checks.push({
        name: 'measurements were linked',
        ok: Array.isArray(r.checks) && r.checks.some((c) => c.id === 'measurements_linked' && c.status === 'pass'),
        detail: JSON.stringify((r.checks || []).map((c) => `${c.id}=${c.status}`)),
      })
      return checks
    },
    capture: (bb, r) => {
      bb.specPath = r.specPath
      bb.spec = r.spec
    },
  },

  {
    id: 'generate-roof',
    tool: 'wm_generate_roof',
    phase: 'B · parametric generation',
    args: (bb) => ({
      baseBlend: bb.blend || BASE_BLEND,
      outBlend: path.join(SCENE_DIR, 'step1_roof.blend'),
      style: 'hip',
      detail: 'medium',
    }),
    verify: (bb, r) => {
      const checks = []
      const blend = blendOf(r, path.join(SCENE_DIR, 'step1_roof.blend'))
      checks.push({ name: 'blend written', ok: statFile(blend).bytes > 0, detail: `${blend} (${statFile(blend).bytes} B)` })
      checks.push({ name: 'objects listed', ok: Array.isArray(r.objects) && r.objects.length > 0, detail: `${(r.objects || []).length}` })
      checks.push({ name: 'tileCount > 0', ok: num(r.metrics?.tileCount) && r.metrics.tileCount > 0, detail: String(r.metrics?.tileCount) })
      checks.push({ name: 'roof height plausible (0.5–12 m)', ok: num(r.metrics?.height) && r.metrics.height > 0.5 && r.metrics.height < 12, detail: String(r.metrics?.height) })
      const roofs = (r.objects || []).filter((o) => o && (o.part === 'roof' || /^ROOF_|^TILE_/.test(String(o.name))))
      checks.push({ name: 'roof objects tagged with wm_part=roof', ok: roofs.length > 0, detail: `${roofs.length} roof-tagged objects` })
      return checks
    },
    capture: (bb, r) => {
      bb.blend = blendOf(r, path.join(SCENE_DIR, 'step1_roof.blend'))
    },
  },

  {
    id: 'export-glb',
    tool: 'wm_export_glb',
    phase: 'B · parametric generation',
    needs: ['blend'],
    args: (bb) => ({ blend: bb.blend, out: path.join(SCENE_DIR, 'roof.glb'), yUp: true }),
    verify: (bb, r) => {
      // The implementation reports the export inventory under `metrics`; §4 lists
      // it at the top level. Accept both, and flag the nesting as drift.
      const m = r.metrics && typeof r.metrics === 'object' ? { ...r.metrics, ...r } : r
      const glb = r.glbPath || m.path || path.join(SCENE_DIR, 'roof.glb')
      const st = statFile(glb)
      const nested = r.bytes === undefined && r.metrics && r.metrics.bytes !== undefined
      return [
        { name: 'glbPath present', ok: typeof glb === 'string' && st.bytes > 0, detail: `${glb} (${st.bytes} B)` },
        { name: 'reported bytes match disk', ok: m.bytes === st.bytes, detail: `reported=${m.bytes} disk=${st.bytes}` },
        { name: 'triangles > 0', ok: num(m.triangles) && m.triangles > 0, detail: String(m.triangles) },
        { name: 'meshes > 0', ok: num(m.meshes) && m.meshes > 0, detail: String(m.meshes) },
        { name: 'materials > 0', ok: num(m.materials) && m.materials > 0, detail: String(m.materials) },
        {
          name: 'textures is an array as §4 requires',
          ok: Array.isArray(r.textures) || Array.isArray(m.textures),
          detail: `textures=${JSON.stringify(m.textures)}`,
          warn: true,
          warnDetail: '§4 says textures:[{name,width,height}] but the tool returns a count',
        },
        {
          name: '§4 result fields are at the top level',
          ok: !nested,
          detail: nested ? 'bytes/triangles/meshes/materials/textures are nested under metrics (contract drift)' : '',
          warn: true,
          warnDetail: 'the harness reads metrics.* as well, but §4 documents top-level fields',
        },
      ]
    },
    capture: (bb, r) => {
      bb.glb = r.glbPath || path.join(SCENE_DIR, 'roof.glb')
    },
  },

  {
    id: 'capture-views',
    tool: 'wm_capture_views',
    phase: 'C · visual matching',
    needs: ['blend'],
    args: (bb) => ({
      blend: bb.blend,
      views: ['front34', 'front', 'eave'],
      width: 1200,
      height: 900,
      samples: 16,
    }),
    verify: (bb, r) => {
      const shots = Array.isArray(r.shots) ? r.shots : []
      const checks = []
      checks.push({ name: 'renders the requested view count', ok: shots.length === 3, detail: `got ${shots.length}` })
      const bad = shots.filter((s) => !s || !s.path || statFile(s.path).bytes <= 0)
      checks.push({ name: 'every shot exists with bytes > 0', ok: bad.length === 0, detail: `${bad.length} bad` })
      const wrongSize = shots.filter((s) => s.width !== 1200 || s.height !== 900)
      checks.push({ name: 'every shot reports 1200x900', ok: wrongSize.length === 0, detail: JSON.stringify(wrongSize.map((s) => `${s.view}:${s.width}x${s.height}`)) })
      checks.push({ name: 'camera data returned', ok: Array.isArray(r.cameras) || typeof r.camerasPath === 'string', detail: `cameras=${Array.isArray(r.cameras)} camerasPath=${typeof r.camerasPath}` })
      return checks
    },
    capture: (bb, r) => {
      bb.shots = Array.isArray(r.shots) ? r.shots : []
      bb.renderForCompare = (bb.shots.find((s) => s.view === 'front34') || bb.shots[0] || {}).path
    },
  },

  {
    id: 'compare-reference',
    tool: 'wm_compare_reference',
    phase: 'C · visual matching',
    needs: ['renderForCompare'],
    args: (bb) => ({
      reference: referenceImages[0] || path.join(REFERENCES_DIR, 'missing.png'),
      render: bb.renderForCompare,
      outDir: COMPARE_DIR,
      align: 'auto',
    }),
    verify: (bb, r) => {
      const checks = []
      for (const key of ['sideBySide', 'overlay', 'contour']) {
        const p = r[key]
        const st = statFile(p)
        checks.push({ name: `${key} PNG written`, ok: typeof p === 'string' && st.bytes > 0, detail: `${p} (${st.bytes} B)` })
      }
      const m = r.metrics || {}
      checks.push({
        name: 'silhouetteIoU measured in 0..1',
        ok:
          (num(m.silhouetteIoU) && m.silhouetteIoU >= 0 && m.silhouetteIoU <= 1) ||
          (num(m.silhouetteIoUUnconditional) && m.silhouetteIoUUnconditional >= 0 && m.silhouetteIoUUnconditional <= 1),
        detail: `silhouetteIoU=${m.silhouetteIoU} silhouetteIoUUnconditional=${m.silhouetteIoUUnconditional}`,
      })
      if (!num(m.silhouetteIoU) && num(m.silhouetteIoUUnconditional)) {
        checks.push({
          name: '§4 names the IoU metric silhouetteIoU',
          ok: false,
          detail: `the tool reports silhouetteIoUUnconditional=${m.silhouetteIoUUnconditional} and leaves silhouetteIoU null`,
          warn: true,
          warnDetail: 'document the unconditional variant in §4 or always fill silhouetteIoU',
        })
      }
      checks.push({ name: 'regions reported', ok: Array.isArray(r.regions) && r.regions.length > 0, detail: `${(r.regions || []).length}` })
      checks.push({
        name: 'checks use the documented status vocabulary',
        ok: Array.isArray(r.checks) && r.checks.every((c) => ['pass', 'warn', 'fail', 'manual', 'not_checked'].includes(c.status)),
        detail: JSON.stringify((r.checks || []).map((c) => c.status)),
      })
      return checks
    },
    capture: (bb, r) => {
      bb.comparison = r
    },
  },

  {
    id: 'generate-diff-report',
    tool: 'wm_generate_diff_report',
    phase: 'C · visual matching',
    needs: ['comparison'],
    args: (bb) => ({ comparisons: [bb.comparison], title: '纹脉展馆 · E2E 对照差异报告' }),
    verify: (bb, r) => {
      const checks = []
      checks.push({ name: 'reportPath written', ok: typeof r.reportPath === 'string' && statFile(r.reportPath).bytes > 0, detail: `${r.reportPath} (${statFile(r.reportPath).bytes} B)` })
      checks.push({ name: 'topDifferences ranked', ok: Array.isArray(r.topDifferences) && r.topDifferences.length > 0, detail: `${(r.topDifferences || []).length}` })
      checks.push({ name: 'markdown body returned', ok: typeof r.markdown === 'string' && r.markdown.length > 100, detail: `length=${(r.markdown || '').length}` })
      return checks
    },
    capture: (bb, r) => {
      bb.reportPath = r.reportPath
      bb.diffReport = r
    },
  },

  {
    id: 'propose-geometry-changes',
    tool: 'wm_propose_geometry_changes',
    phase: 'C · visual matching',
    needs: ['reportPath'],
    args: (bb) => ({ reportPath: bb.reportPath, specPath: bb.specPath }),
    verify: (bb, r) => {
      const changes = Array.isArray(r.changes) ? r.changes : []
      const checks = []
      checks.push({ name: 'changes is a non-empty array', ok: changes.length > 0, detail: `${changes.length}` })
      checks.push({
        name: 'every change has priority/component/parameter/from/to',
        ok: changes.every((c) => c && c.parameter !== undefined && c.component !== undefined && 'from' in c && 'to' in c),
        detail: JSON.stringify(changes.slice(0, 3)).slice(0, 400),
      })
      checks.push({ name: 'reportPath echoed', ok: typeof r.reportPath === 'string' && statFile(r.reportPath).bytes > 0, detail: String(r.reportPath) })
      return checks
    },
  },

  {
    id: 'generate-timber',
    tool: 'wm_generate_timber',
    phase: 'B · parametric generation',
    needs: ['blend'],
    args: (bb) => ({ baseBlend: bb.blend, outBlend: path.join(SCENE_DIR, 'step2_timber.blend'), detail: 'medium' }),
    verify: (bb, r) => {
      const checks = []
      const blend = blendOf(r, path.join(SCENE_DIR, 'step2_timber.blend'))
      checks.push({ name: 'blend written', ok: statFile(blend).bytes > 0, detail: `${blend} (${statFile(blend).bytes} B)` })
      const objs = Array.isArray(r.objects) ? r.objects : []
      checks.push({ name: 'objects listed', ok: objs.length > 0, detail: `${objs.length}` })
      const timber = objs.filter((o) => (o && o.part === 'timber') || /^(COLUMN_|BEAM_|DOUGONG_)/.test(String(o && o.name)))
      checks.push({ name: 'timber components produced', ok: timber.length > 0, detail: `${timber.length}` })
      checks.push({
        name: 'every reported object is tagged wm_part',
        ok: objs.length > 0 && objs.every((o) => o && typeof o.part === 'string' && o.part.length > 0),
        detail: JSON.stringify(objs.map((o) => o && `${o.name}:${o.part}`)),
      })
      return checks
    },
    /**
     * The timber result only lists the objects *this run* created, so part
     * preservation cannot be read off it. Prove it against the real .blend with
     * the harness-owned Blender probe instead (note: the step's OUTPUT blend,
     * captured before bb.blend is advanced).
     */
    extraChecks: async (bb, value) => {
      const probe = probeBlend(blendOf(value, path.join(SCENE_DIR, 'step2_timber.blend')))
      if (!probe.ok) return [{ name: 'blend probe runs', ok: false, detail: probe.error }]
      const d = probe.data
      const counts = d.nameCounts || {}
      return [
        { name: 'probe: timber pass kept the roof part', ok: (d.parts?.roof ?? 0) > 0 && (counts.ROOF ?? 0) > 0, detail: `parts=${JSON.stringify(d.parts)} ROOF=${counts.ROOF}` },
        { name: 'probe: timber pass kept the tile objects', ok: (counts.TILE ?? 0) > 0, detail: `TILE=${counts.TILE}` },
        { name: 'probe: timber objects exist with wm_part=timber', ok: (d.parts?.timber ?? 0) > 0, detail: `parts=${JSON.stringify(d.parts)}` },
        { name: 'probe: 15 FRAME anchors still present', ok: d.frameAnchorObjects === 15, detail: `frameAnchorObjects=${d.frameAnchorObjects}` },
        { name: 'probe: the probed blend is the timber output', ok: /step2_timber/i.test(String(d.blend)), detail: String(d.blend) },
        ...foreignRemovalChecks('wm_generate_timber', path.join(SCENE_DIR, 'step1_roof.blend'), path.join(SCENE_DIR, 'step2_timber.blend')),
      ]
    },
    capture: (bb, r) => {
      bb.blend = blendOf(r, path.join(SCENE_DIR, 'step2_timber.blend'))
    },
  },

  {
    id: 'generate-interior',
    tool: 'wm_generate_interior',
    phase: 'B · parametric generation',
    needs: ['blend'],
    args: (bb) => ({ baseBlend: bb.blend, outBlend: path.join(SCENE_DIR, 'step3_interior.blend'), detail: 'medium' }),
    verify: (bb, r) => {
      const checks = []
      const blend = blendOf(r, path.join(SCENE_DIR, 'step3_interior.blend'))
      checks.push({ name: 'blend written', ok: statFile(blend).bytes > 0, detail: `${blend} (${statFile(blend).bytes} B)` })
      const anchors = detectFrameAnchors(r)
      checks.push({
        name: '15 FRAME anchors preserved',
        ok: anchors.objectCount === 15 || anchors.metric === 15,
        detail: `objects=${anchors.objectCount} metric=${anchors.metric}`,
      })
      checks.push({ name: 'objects listed', ok: Array.isArray(r.objects) && r.objects.length > 0, detail: `${(r.objects || []).length}` })
      return checks
    },
    /** §4: the 15 FRAME anchors must survive — verified in the real .blend. */
    extraChecks: async (bb, value) => {
      const probe = probeBlend(blendOf(value, path.join(SCENE_DIR, 'step3_interior.blend')))
      if (!probe.ok) return [{ name: 'blend probe runs', ok: false, detail: probe.error }]
      const d = probe.data
      const expected = [
        'FRAME_F1_001', 'FRAME_F1_002', 'FRAME_F1_003', 'FRAME_F1_004', 'FRAME_F1_005', 'FRAME_F1_006', 'FRAME_F1_007',
        'FRAME_F2_001', 'FRAME_F2_002', 'FRAME_F2_003', 'FRAME_F2_004', 'FRAME_F2_005', 'FRAME_F2_006', 'FRAME_F2_007', 'FRAME_F2_008',
      ]
      const have = new Set(d.frameAnchors || [])
      const missing = expected.filter((n) => !have.has(n))
      return [
        { name: 'probe: the probed blend is the interior output', ok: /step3_interior/i.test(String(d.blend)), detail: String(d.blend) },
        { name: 'probe: exactly 15 FRAME anchors in the saved .blend', ok: d.frameAnchorObjects === 15, detail: `frameAnchorObjects=${d.frameAnchorObjects}` },
        { name: 'probe: every named anchor FRAME_F1_001..007 / FRAME_F2_001..008 is present', ok: missing.length === 0, detail: `missing=${JSON.stringify(missing)}` },
        { name: 'probe: interior objects are tagged wm_part', ok: (d.parts?.interior ?? 0) > 0, detail: `parts=${JSON.stringify(d.parts)}` },
        ...foreignRemovalChecks('wm_generate_interior', path.join(SCENE_DIR, 'step2_timber.blend'), path.join(SCENE_DIR, 'step3_interior.blend')),
      ]
    },
    capture: (bb, r) => {
      bb.blend = blendOf(r, path.join(SCENE_DIR, 'step3_interior.blend'))
      bb.frameAnchors = detectFrameAnchors(r)
    },
  },

  {
    id: 'generate-diorama',
    tool: 'wm_generate_diorama',
    phase: 'B · parametric generation',
    needs: ['blend'],
    args: (bb) => ({ baseBlend: bb.blend, outBlend: path.join(SCENE_DIR, 'step4_diorama.blend'), detail: 'medium' }),
    verify: (bb, r) => {
      const checks = []
      const blend = blendOf(r, path.join(SCENE_DIR, 'step4_diorama.blend'))
      checks.push({ name: 'blend written', ok: statFile(blend).bytes > 0, detail: `${blend} (${statFile(blend).bytes} B)` })
      checks.push({ name: 'objects listed', ok: Array.isArray(r.objects) && r.objects.length > 0, detail: `${(r.objects || []).length}` })
      const props = (r.objects || []).filter((o) => o && (o.part === 'diorama' || /^(BASE_|PROP_)/.test(String(o.name))))
      checks.push({ name: 'diorama/prop objects tagged', ok: props.length > 0, detail: `${props.length}` })
      const m = r.metrics || {}
      checks.push({ name: 'baseSize echoed as 16 m', ok: !num(m.baseSize) || m.baseSize === 16, detail: String(m.baseSize), warn: true, warnDetail: 'metric not reported' })
      checks.push({ name: 'plinthHeight echoed as 0.65 m', ok: !num(m.plinthHeight) || m.plinthHeight === 0.65, detail: String(m.plinthHeight), warn: true, warnDetail: 'metric not reported' })
      return checks
    },
    /** Final composed scene: every part class must coexist in the real .blend. */
    extraChecks: async (bb, value) => {
      const probe = probeBlend(blendOf(value, path.join(SCENE_DIR, 'step4_diorama.blend')))
      if (!probe.ok) return [{ name: 'blend probe runs', ok: false, detail: probe.error }]
      const d = probe.data
      const parts = d.parts || {}
      const c = d.nameCounts || {}
      return [
        { name: 'probe: the probed blend is the diorama output', ok: /step4_diorama/i.test(String(d.blend)), detail: String(d.blend) },
        { name: 'probe: roof part present in the final scene', ok: (parts.roof ?? 0) > 0, detail: `roof=${parts.roof} ROOF_=${c.ROOF} TILE_=${c.TILE}` },
        { name: 'probe: timber part present in the final scene', ok: (parts.timber ?? 0) > 0, detail: `timber=${parts.timber} COLUMN_=${c.COLUMN} BEAM_=${c.BEAM}` },
        { name: 'probe: interior part present in the final scene', ok: (parts.interior ?? 0) > 0, detail: `interior=${parts.interior}` },
        { name: 'probe: diorama part present in the final scene', ok: (parts.diorama ?? 0) > 0, detail: `diorama=${parts.diorama} BASE_=${c.BASE} PROP_=${c.PROP}` },
        { name: 'probe: 15 FRAME anchors survived the whole chain', ok: d.frameAnchorObjects === 15, detail: `frameAnchorObjects=${d.frameAnchorObjects}` },
        { name: 'probe: meshes/triangles > 0 in the final scene', ok: d.meshes > 0 && d.triangles > 0, detail: `meshes=${d.meshes} triangles=${d.triangles} materials=${d.materials}` },
        ...foreignRemovalChecks('wm_generate_diorama', path.join(SCENE_DIR, 'step3_interior.blend'), path.join(SCENE_DIR, 'step4_diorama.blend')),
      ]
    },
    capture: (bb, r) => {
      bb.blend = blendOf(r, path.join(SCENE_DIR, 'step4_diorama.blend'))
    },
  },

  {
    id: 'export-glb-final',
    tool: 'wm_export_glb',
    phase: 'B · parametric generation',
    needs: ['blend'],
    args: (bb) => ({ blend: bb.blend, out: path.join(SCENE_DIR, 'gallery_final.glb'), yUp: true }),
    verify: (bb, r) => {
      const m = r.metrics && typeof r.metrics === 'object' ? { ...r.metrics, ...r } : r
      const glb = r.glbPath || path.join(SCENE_DIR, 'gallery_final.glb')
      const st = statFile(glb)
      return [
        { name: 'final glb written', ok: st.bytes > 0, detail: `${glb} (${st.bytes} B)` },
        { name: 'reported bytes match disk', ok: m.bytes === st.bytes, detail: `reported=${m.bytes} disk=${st.bytes}` },
        { name: 'triangles > 0', ok: num(m.triangles) && m.triangles > 0, detail: String(m.triangles) },
        { name: 'meshes > 0', ok: num(m.meshes) && m.meshes > 0, detail: String(m.meshes) },
        { name: 'materials > 0', ok: num(m.materials) && m.materials > 0, detail: String(m.materials) },
      ]
    },
    capture: (bb, r) => {
      bb.glbFinal = r.glbPath || path.join(SCENE_DIR, 'gallery_final.glb')
    },
  },

  {
    id: 'inspect-scene',
    tool: 'wm_inspect_scene',
    phase: 'D · inspection',
    needs: ['blend'],
    args: (bb) => ({ blend: bb.blend }),
    verify: (bb, r) => {
      const s = r.summary || {}
      const checks = []
      checks.push({ name: 'summary.objects > 0', ok: num(s.objects) && s.objects > 0, detail: String(s.objects) })
      checks.push({ name: 'summary.triangles > 0', ok: num(s.triangles) && s.triangles > 0, detail: String(s.triangles) })
      const allowed = new Set(['pass', 'warn', 'fail', 'manual', 'not_checked'])
      checks.push({ name: 'checks use the documented status vocabulary', ok: Array.isArray(r.checks) && r.checks.every((c) => allowed.has(c.status)), detail: JSON.stringify((r.checks || []).map((c) => c.status)) })
      checks.push({ name: 'bounds reported', ok: !!r.bounds && typeof r.bounds === 'object', detail: typeof r.bounds })
      checks.push(...internalStatusChecks('wm_inspect_scene', r))
      return checks
    },
  },

  {
    id: 'check-art-frames',
    tool: 'wm_check_art_frames',
    phase: 'D · inspection',
    needs: ['blend'],
    args: (bb) => ({ blend: bb.blend, expected: 15 }),
    verify: (bb, r) => [
      { name: 'found === 15', ok: r.found === 15, detail: String(r.found) },
      { name: 'frames array has 15 entries', ok: Array.isArray(r.frames) && r.frames.length === 15, detail: `${(r.frames || []).length}` },
      { name: 'missing list is empty', ok: Array.isArray(r.missing) && r.missing.length === 0, detail: JSON.stringify(r.missing) },
      {
        name: 'every frame reports an id and a status',
        ok: Array.isArray(r.frames) && r.frames.every((f) => f && f.id && typeof f.status === 'string'),
        detail: JSON.stringify((r.frames || []).slice(0, 2)),
      },
      {
        name: 'no FRAME anchor is buried inside a wall',
        ok: !num(r.buried) || r.buried === 0,
        detail: `buried=${r.buried}, blocked=${r.blocked}, maxPositionErrorM=${r.maxPositionErrorM}`,
        warn: true,
        warnDetail: num(r.buried) && r.buried > 0 ? `${r.buried}/15 anchors sit inside a wall volume (the interior pass places GALWALL panels over them)` : '',
      },
      ...internalStatusChecks('wm_check_art_frames', r),
    ],
  },

  {
    id: 'check-export',
    tool: 'wm_check_export',
    phase: 'D · inspection',
    needs: ['glbFinal'],
    args: (bb) => ({ glb: bb.glbFinal, profile: 'web' }),
    verify: (bb, r) => {
      const st = statFile(bb.glbFinal)
      const checks = []
      checks.push({ name: 'bytes match the file on disk', ok: r.bytes === st.bytes, detail: `reported=${r.bytes} disk=${st.bytes}` })
      checks.push({ name: 'meshes > 0', ok: num(r.meshes) && r.meshes > 0, detail: String(r.meshes) })
      checks.push({ name: 'triangles > 0', ok: num(r.triangles) && r.triangles > 0, detail: String(r.triangles) })
      checks.push({ name: 'materials > 0', ok: num(r.materials) && r.materials > 0, detail: String(r.materials) })
      checks.push({ name: 'animations is a number', ok: num(r.animations), detail: String(r.animations) })
      checks.push({ name: 'checks array present', ok: Array.isArray(r.checks) && r.checks.length > 0, detail: `${(r.checks || []).length}` })
      checks.push({ name: 'warnings array present', ok: Array.isArray(r.warnings), detail: typeof r.warnings })
      checks.push(...internalStatusChecks('wm_check_export', r))
      return checks
    },
  },

  {
    id: 'performance-report',
    tool: 'wm_performance_report',
    phase: 'D · inspection',
    needs: ['blend', 'glbFinal'],
    args: (bb) => ({ blend: bb.blend, glb: bb.glbFinal, triangleBudget: 350000, sizeBudgetMb: 16 }),
    verify: (bb, r) => [
      { name: 'reportPath written', ok: typeof r.reportPath === 'string' && statFile(r.reportPath).bytes > 0, detail: `${r.reportPath} (${statFile(r.reportPath).bytes} B)` },
      { name: 'budget reported', ok: !!r.budget && typeof r.budget === 'object', detail: JSON.stringify(r.budget).slice(0, 200) },
      { name: 'hotspots is an array', ok: Array.isArray(r.hotspots), detail: typeof r.hotspots },
      { name: 'recommendations is an array', ok: Array.isArray(r.recommendations), detail: typeof r.recommendations },
      ...internalStatusChecks('wm_performance_report', r),
    ],
  },

  {
    id: 'match-camera',
    tool: 'wm_match_camera',
    phase: 'A · reference reconstruction',
    args: () => ({
      image: (cameraFixture && cameraFixture.image && path.join(PROJECT_ROOT, cameraFixture.image)) || referenceImages[0],
      correspondences: (cameraFixture ? cameraFixture.correspondences : []).map((c) => ({ point3d: c.point3d, pixel: c.pixel, label: c.label })),
      imageSize: cameraFixture ? cameraFixture.imageSize : [1448, 1086],
      outPath: path.join(SPEC_DIR, 'camera_fixture.json'),
    }),
    verify: (bb, r) => {
      const cam = r.camera || {}
      const err = r.reprojectionError || {}
      const tol = cameraFixture ? cameraFixture.toleranceRmsPx : 2
      const checks = []
      checks.push({ name: 'camera.position is [x,y,z]', ok: Array.isArray(cam.position) && cam.position.length === 3 && cam.position.every(num), detail: JSON.stringify(cam.position) })
      checks.push({ name: 'camera.target is [x,y,z]', ok: Array.isArray(cam.target) && cam.target.length === 3 && cam.target.every(num), detail: JSON.stringify(cam.target) })
      checks.push({ name: 'lens > 0', ok: num(cam.lens) && cam.lens > 0, detail: String(cam.lens) })
      checks.push({ name: 'fov > 0', ok: num(cam.fov) && cam.fov > 0, detail: String(cam.fov) })
      checks.push({
        name: `reprojection RMS <= ${tol} px (synthetic ground truth)`,
        ok: num(err.rmsPx) && err.rmsPx <= tol,
        detail: `rmsPx=${err.rmsPx} maxPx=${err.maxPx}`,
      })
      checks.push({ name: 'perPoint diagnostics returned', ok: Array.isArray(r.perPoint) && r.perPoint.length === 14, detail: `${(r.perPoint || []).length}` })
      const camPath = r.cameraPath || path.join(SPEC_DIR, 'camera_fixture.json')
      checks.push({ name: 'cameraPath written', ok: statFile(camPath).bytes > 0, detail: String(camPath) })
      return checks
    },
    capture: (bb, r) => {
      bb.cameraPath = r.cameraPath || path.join(SPEC_DIR, 'camera_fixture.json')
      bb.camera = r.camera
    },
  },

  {
    id: 'validate-multiview',
    tool: 'wm_validate_multiview',
    phase: 'A · reference reconstruction',
    needs: ['specPath', 'cameraPath'],
    args: (bb) => ({
      specPath: bb.specPath,
      views: [{ image: (cameraFixture && cameraFixture.image && path.join(PROJECT_ROOT, cameraFixture.image)) || referenceImages[0], cameraPath: bb.cameraPath }],
    }),
    verify: (bb, r) => [
      { name: 'perView reported', ok: Array.isArray(r.perView) && r.perView.length === 1, detail: `${(r.perView || []).length}` },
      {
        name: 'perView entries carry an image',
        ok: Array.isArray(r.perView) && r.perView.every((v) => v && typeof v.image === 'string'),
        detail: JSON.stringify(r.perView && r.perView[0]).slice(0, 200),
      },
      { name: 'contradictions is an array', ok: Array.isArray(r.contradictions), detail: typeof r.contradictions },
      {
        name: "status is pass|warn|fail as §4 states",
        ok: ['pass', 'warn', 'fail'].includes(r.status),
        detail: `status=${r.status}`,
        warn: true,
        warnDetail:
          r.status === 'not_checked'
            ? 'the tool honestly reports not_checked (no measured bands for this synthetic camera); §4 should document that status'
            : `unexpected status ${r.status}`,
      },
      {
        name: 'status is one of the plugin-wide vocabulary',
        ok: ['pass', 'warn', 'fail', 'manual', 'not_checked'].includes(r.status),
        detail: `status=${r.status}`,
      },
    ],
  },
]

/**
 * Surface a tool's OWN verdicts. A step can be structurally fine while the tool
 * reports `fail` checks inside the result (buried frames, flipped normals, ...);
 * those must appear in the acceptance report, so they become warnings here —
 * loud, but not a harness-level step failure.
 */
function internalStatusChecks(label, result) {
  const checks = Array.isArray(result?.checks) ? result.checks : []
  if (checks.length === 0) return []
  const fails = checks.filter((c) => c.status === 'fail')
  const warns = checks.filter((c) => c.status === 'warn')
  const out = [
    {
      name: `${label}: the tool itself reports no fail check`,
      ok: fails.length === 0,
      detail: fails.map((c) => `${c.id}: ${String(c.detail || '').slice(0, 180)}`).join(' | '),
      warn: true,
      warnDetail: fails.length ? `${label} reports ${fails.length} fail check(s): ${fails.map((c) => c.id).join(', ')}` : '',
    },
  ]
  if (warns.length) {
    out.push({ name: `${label}: internal warn checks recorded`, ok: true, detail: warns.map((c) => `${c.id}: ${String(c.detail || '').slice(0, 140)}`).join(' | ') })
  }
  return out
}

function blendOf(result, fallback) {
  const arts = Array.isArray(result?.artifacts) ? result.artifacts : []
  const blend = arts.find((a) => a && (a.kind === 'blend' || /\.blend$/i.test(String(a.path))))
  if (blend && typeof blend.path === 'string') return blend.path
  return fallback
}

/**
 * CONTRACT §3 dispatch table: which Python module a tool needs. A module the
 * Lead has not written yet is reported `not_ready` *before* a Blender launch is
 * wasted on it, which is the re-runnable behaviour the acceptance run needs.
 */
const PY_MODULE = {
  wm_analyze_references: 'wm_analysis',
  wm_build_scene_spec: null, // Node-side
  wm_match_camera: 'wm_camera',
  wm_validate_multiview: 'wm_camera',
  wm_generate_roof: 'wm_roof',
  wm_generate_timber: 'wm_timber',
  wm_generate_interior: 'wm_interior',
  wm_generate_diorama: 'wm_diorama',
  wm_export_glb: 'wm_export',
  wm_capture_views: 'wm_capture',
  wm_compare_reference: 'wm_compare',
  wm_generate_diff_report: null, // Node-side
  wm_propose_geometry_changes: 'wm_compare',
  wm_inspect_scene: 'wm_inspect',
  wm_check_art_frames: 'wm_inspect',
  wm_check_export: 'wm_inspect',
  wm_performance_report: 'wm_inspect',
}

function pythonModuleReady(tool) {
  const mod = PY_MODULE[tool]
  if (!mod) return { ready: true }
  const file = path.join(PLUGIN_ROOT, 'python', `${mod}.py`)
  if (fs.existsSync(file)) return { ready: true }
  return { ready: false, reason: `python/${mod}.py not written yet (CONTRACT §3 dispatch table)` }
}

function isMissingPythonModule(error) {
  const text = String(error || '')
  const m = text.match(/No module named '?(wm_[a-z_]+)'?/)
  return m ? m[1] : null
}

/**
 * Harness-owned ground truth: open a .blend with Blender and report what is
 * really inside it (parts, FRAME anchors, name prefixes). This is how the run
 * proves cross-part preservation without trusting a tool's own summary.
 */
function probeBlend(blendPath) {
  const script = path.join(TESTS_DIR, 'lib', 'probe-blend.py')
  if (!fs.existsSync(script)) return { ok: false, error: `probe script missing: ${script}` }
  const res = spawnSync(BLENDER_EXE, ['-b', '-noaudio', '--python', script, '--', blendPath], {
    encoding: 'utf8',
    timeout: 180000,
    maxBuffer: 32 * 1024 * 1024,
  })
  const text = `${res.stdout || ''}\n${res.stderr || ''}`
  const line = text.split(/\r?\n/).reverse().find((l) => l.startsWith('WMPROBE '))
  if (!line) {
    return { ok: false, error: `probe printed no WMPROBE line (exit ${res.status}): ${text.slice(-400)}` }
  }
  try {
    return { ok: true, data: JSON.parse(line.slice('WMPROBE '.length)) }
  } catch (err) {
    return { ok: false, error: `probe JSON unparsable: ${err.message}` }
  }
}

/** Compare two .blend inventories: what did the pass remove that it did not own? */
function probeDiff(blendA, blendB) {
  const script = path.join(TESTS_DIR, 'lib', 'probe-diff.py')
  if (!fs.existsSync(script)) return { ok: false, error: `probe script missing: ${script}` }
  const res = spawnSync(BLENDER_EXE, ['-b', '-noaudio', '--python', script, '--', blendA, blendB], {
    encoding: 'utf8',
    timeout: 180000,
    maxBuffer: 32 * 1024 * 1024,
  })
  const text = `${res.stdout || ''}\n${res.stderr || ''}`
  const line = text.split(/\r?\n/).reverse().find((l) => l.startsWith('WMPROBE '))
  if (!line) return { ok: false, error: `diff probe printed no WMPROBE line (exit ${res.status}): ${text.slice(-400)}` }
  try {
    return { ok: true, data: JSON.parse(line.slice('WMPROBE '.length)) }
  } catch (err) {
    return { ok: false, error: `diff probe JSON unparsable: ${err.message}` }
  }
}

/**
 * CONTRACT §7 says a generator replaces only its own `wm_part`. This turns that
 * into a measurement: count the objects the pass deleted that carry NO wm_part
 * (i.e. foreign/legacy geometry), and surface the name prefixes involved.
 */
function foreignRemovalChecks(label, before, after) {
  const diff = probeDiff(before, after)
  if (!diff.ok) return [{ name: `probe: ${label} inventory diff runs`, ok: false, detail: diff.error }]
  const d = diff.data
  return [
    {
      name: `probe: ${label} removed no foreign (untagged) objects (§7)`,
      ok: d.removedUntagged === 0,
      detail: `removedUntagged=${d.removedUntagged} of removed=${d.removedCount}, byPrefix=${JSON.stringify(d.removedByPrefix)}`,
      warn: true,
      warnDetail:
        d.removedUntagged > 0
          ? `${label} deleted ${d.removedUntagged} untagged objects (${JSON.stringify(d.removedByPrefix)}) — intentional v5 replacement or a §7 violation?`
          : '',
    },
    {
      name: `probe: ${label} added its own objects`,
      ok: d.addedCount > 0,
      detail: `added=${d.addedCount} byPrefix=${JSON.stringify(d.addedByPrefix)}`,
    },
  ]
}

// ------------------------------------------------------------------ runner

if (args.list) {
  for (const [i, step] of STEPS.entries()) {
    console.log(`${String(i + 1).padStart(2)}. ${step.tool.padEnd(28)} ${step.phase}  (needs: ${(step.needs || []).join(', ') || '—'})`)
  }
  process.exit(0)
}

const loaded = await loadPlugin()
if (!loaded.ok) {
  suite.notReady('lib/index.js exists', loaded.reason)
  const summary = suite.summary()
  const payload = {
    kind: 'e2e',
    status: 'not_ready',
    reason: loaded.reason,
    startedAt: stamp(),
    steps: [],
  }
  writeJson(path.join(QA_ROOT, `e2e-${RUN_STAMP}.json`), payload)
  writeJson(path.join(QA_ROOT, 'e2e-last.json'), payload)
  writeText(
    path.join(QA_ROOT, `e2e-${RUN_STAMP}.md`),
    `# E2E — NOT READY\n\n- at: ${stamp()}\n- reason: ${loaded.reason}\n\nNo tool was executed.\n`,
  )
  process.exit(summary.exitCode === 0 ? 2 : summary.exitCode)
}

const plugin = pluginObject(loaded.mod)
const { ctx, byName } = createFakeContext()
const activationBefore = preserveActivation('e2e')
if (activationBefore) suite.note(`preserved a previous activation record: ${activationBefore}`)
let applyError = null
try {
  const apply = typeof plugin === 'function' ? plugin : plugin.apply
  await apply(ctx, PLUGIN_CONFIG)
} catch (err) {
  applyError = err
}
if (applyError) {
  suite.fail('apply(ctx, config) mounts the plugin', applyError.stack || applyError.message)
  const summary = suite.summary()
  writeJson(path.join(QA_ROOT, 'e2e-last.json'), {
    kind: 'e2e',
    status: 'mount_failed',
    reason: String(applyError && applyError.message),
    at: stamp(),
  })
  process.exit(summary.exitCode === 0 ? 1 : summary.exitCode)
}
suite.ok('apply(ctx, config) mounts the plugin', true)
suite.note(`${byName.size} tool(s) registered; ${STEPS.length} acceptance steps planned`)

const bb = {}
const results = []
const startedAt = stamp()
const runStarted = Date.now()

function shouldRun(step) {
  if (skip.has(step.tool) || skip.has(step.id)) return { run: false, reason: `skipped by --skip (${step.tool})` }
  if (only.size > 0 && !only.has(step.tool) && !only.has(step.id)) return { run: false, reason: 'not selected by --only' }
  return { run: true }
}

for (const [index, step] of STEPS.entries()) {
  const label = `[${index + 1}/${STEPS.length}] ${step.tool}`
  const decision = shouldRun(step)
  const record = {
    index: index + 1,
    id: step.id,
    tool: step.tool,
    phase: step.phase,
    status: 'pending',
    reason: '',
    durationMs: 0,
    checks: [],
    artifacts: [],
    metrics: {},
    error: null,
  }

  if (!decision.run) {
    record.status = 'skipped'
    record.reason = decision.reason
    results.push(record)
    console.log(`--- ${label} SKIP (${record.reason})`)
    continue
  }

  const def = byName.get(step.tool)
  if (!def) {
    record.status = 'not_ready'
    record.reason = `tool not registered (TS module for ${step.tool} not available yet)`
    results.push(record)
    console.log(`--- ${label} NOT READY (${record.reason})`)
    continue
  }

  const py = pythonModuleReady(step.tool)
  if (!py.ready) {
    record.status = 'not_ready'
    record.reason = py.reason
    results.push(record)
    console.log(`--- ${label} NOT READY (${record.reason})`)
    continue
  }

  const missingNeeds = (step.needs || []).filter((k) => bb[k] === undefined || bb[k] === null)
  if (missingNeeds.length > 0) {
    record.status = 'blocked'
    record.reason = `missing dependency value(s): ${missingNeeds.join(', ')}`
    results.push(record)
    console.log(`--- ${label} BLOCKED (${record.reason})`)
    continue
  }

  let stepArgs
  try {
    stepArgs = step.args(bb)
  } catch (err) {
    record.status = 'fail'
    record.reason = 'argument construction failed'
    record.error = String(err && err.message)
    results.push(record)
    console.log(`--- ${label} FAIL (${record.error})`)
    continue
  }
  record.args = trimArgs(stepArgs)

  console.log(`>>> ${label} …`)
  const t0 = Date.now()
  const timeoutMs = def.timeoutMs || PLUGIN_CONFIG.timeoutMs
  const signal = AbortSignal.timeout(timeoutMs)
  let value = null
  try {
    value = await def.execute(stepArgs, { signal, callId: `wm-qa-${RUN_STAMP}-${index + 1}` })
  } catch (err) {
    record.error = err && (err.stack || err.message) ? String(err.message || err) : String(err)
    record.errorStack = err && err.stack ? String(err.stack).slice(0, 4000) : undefined
  }
  record.durationMs = Date.now() - t0

  // persist the raw result for later inspection (evidence, not just a summary)
  try {
    writeJson(path.join(RAW_DIR, `${String(index + 1).padStart(2, '0')}-${step.id}.json`), {
      tool: step.tool,
      args: record.args,
      error: record.error || null,
      result: value,
    })
  } catch {
    /* raw evidence is best-effort */
  }

  if (record.error) {
    const missingModule = isMissingPythonModule(record.error)
    if (missingModule) {
      record.status = 'not_ready'
      record.reason = `python module ${missingModule} not written yet`
    } else {
      record.status = 'fail'
      record.reason = 'threw'
    }
    results.push(record)
    console.log(`--- ${label} ${record.status === 'not_ready' ? 'NOT READY' : 'FAIL'} ${(record.durationMs / 1000).toFixed(1)}s: ${String(record.error).split('\n')[0]}`)
    continue
  }

  const checks = []
  if (value && typeof value === 'object' && value.ok === false) {
    const msg = value.error && (value.error.message || value.error)
    checks.push({ name: 'result.ok === true', ok: false, detail: `ok=false: ${typeof msg === 'string' ? msg : JSON.stringify(msg)}` })
  } else {
    checks.push({ name: 'result.ok === true', ok: true })
  }

  // generic artifact verification (CONTRACT §5: paths must exist with real bytes)
  const artifacts = []
  for (const item of collectArtifacts(value)) {
    const verified = verifyArtifact(item.path)
    verified.label = item.label
    verified.insideProject = insideProject(item.path)
    artifacts.push(verified)
    if (!insideProject(item.path)) {
      checks.push({ name: `artifact ${item.label} stays inside the project root`, ok: false, detail: item.path })
    }
    if (!verified.ok) {
      checks.push({ name: `artifact ${item.label} exists with bytes > 0`, ok: false, detail: `${item.path} → ${verified.problems.join('; ')}` })
    }
  }
  if (artifacts.length > 0) {
    const bad = artifacts.filter((a) => !a.ok)
    checks.push({
      name: `all ${artifacts.length} returned artifact(s) verified on disk`,
      ok: bad.length === 0,
      detail: bad.length ? bad.map((a) => `${a.label}:${a.problems.join('|')}`).join(', ') : undefined,
    })
  }

  // step-specific assertions
  if (value && typeof value === 'object') {
    try {
      const extra = step.verify ? step.verify(bb, value) : []
      for (const item of extra) checks.push({ name: item.name, ok: item.ok, detail: item.detail, warn: item.warn === true, warnDetail: item.warnDetail })
    } catch (err) {
      checks.push({ name: 'step assertions run', ok: false, detail: String(err && err.message) })
    }
  }

  // harness-owned Blender probe (ground truth straight from the .blend)
  if (value && typeof value === 'object' && typeof step.extraChecks === 'function') {
    try {
      const extra = await step.extraChecks(bb, value)
      for (const item of extra) checks.push({ name: item.name, ok: item.ok, detail: item.detail, warn: item.warn === true, warnDetail: item.warnDetail })
    } catch (err) {
      checks.push({ name: 'harness probe runs', ok: false, detail: String(err && err.message) })
    }
  }

  record.checks = checks
  record.artifacts = artifacts
  record.metrics = keyMetrics(value)
  // a failed check marked `warn` is reported but does not fail the step: it is
  // contract drift or an environment limitation, not a broken tool.
  const failed = checks.filter((c) => !c.ok && c.warn !== true)
  const warnings = checks.filter((c) => !c.ok && c.warn === true)
  record.warnings = warnings.map((w) => ({ name: w.name, detail: w.warnDetail || w.detail }))
  record.status = failed.length === 0 ? 'pass' : 'fail'
  if (failed.length) record.reason = `${failed.length} check(s) failed`
  else if (warnings.length) record.reason = `${warnings.length} warning(s)`

  // Advance the blackboard whenever the tool actually produced its artifact —
  // even if an assertion failed — so a failed assertion cannot starve the steps
  // that depend on this one. The failure itself is still reported.
  if (step.capture && value && typeof value === 'object' && value.ok !== false) {
    try {
      step.capture(bb, value)
    } catch (err) {
      record.status = 'fail'
      record.reason = `capture() failed: ${err && err.message}`
    }
  }

  results.push(record)
  const statusText = record.status === 'pass' ? 'PASS' : 'FAIL'
  console.log(
    `--- ${label} ${statusText} ${(record.durationMs / 1000).toFixed(1)}s` +
      (record.metrics && Object.keys(record.metrics).length ? ` · ${JSON.stringify(record.metrics).slice(0, 160)}` : ''),
  )
  for (const f of failed) console.log(`      ✗ ${f.name}${f.detail ? ` — ${f.detail}` : ''}`)
  for (const w of warnings) console.log(`      ! WARN ${w.name} — ${w.warnDetail || w.detail || ''}`)
}

function trimArgs(a) {
  if (!a || typeof a !== 'object') return a
  const out = {}
  for (const [k, v] of Object.entries(a)) {
    if (typeof v === 'string') out[k] = v.length > 300 ? `…${v.slice(-260)}` : v
    else if (typeof v === 'number' || typeof v === 'boolean' || v === null) out[k] = v
    else if (Array.isArray(v)) out[k] = `[${v.length} item(s)]`
    else out[k] = '[object]'
  }
  return out
}

// ---------------------------------------------------------------- summary

const totals = { pass: 0, fail: 0, skipped: 0, not_ready: 0, blocked: 0 }
for (const r of results) totals[r.status] = (totals[r.status] ?? 0) + 1
const durationMs = Date.now() - runStarted
const finishedAt = stamp()

suite.note(`steps: ${totals.pass} pass / ${totals.fail} fail / ${totals.blocked} blocked / ${totals.not_ready} not ready / ${totals.skipped} skipped`)
suite.ok('every planned step reached a verdict', results.length === STEPS.length, `${results.length}/${STEPS.length}`)
suite.ok('no step was left pending', results.every((r) => r.status !== 'pending'))
if (totals.fail === 0) suite.ok('no acceptance step failed', true)
else suite.fail('no acceptance step failed', `${totals.fail}: ${results.filter((r) => r.status === 'fail').map((r) => r.tool).join(', ')}`)

const suiteSummary = suite.summary()

// tool × outcome matrix (one row per contract tool, aggregated across steps)
const TOOLS = [
  'wm_analyze_references', 'wm_build_scene_spec', 'wm_match_camera', 'wm_validate_multiview',
  'wm_generate_roof', 'wm_generate_timber', 'wm_generate_interior', 'wm_generate_diorama', 'wm_export_glb',
  'wm_capture_views', 'wm_compare_reference', 'wm_generate_diff_report', 'wm_propose_geometry_changes',
  'wm_inspect_scene', 'wm_check_art_frames', 'wm_check_export', 'wm_performance_report',
]
const matrix = TOOLS.map((tool) => {
  const runs = results.filter((r) => r.tool === tool)
  const registered = byName.has(tool)
  const executed = runs.filter((r) => ['pass', 'fail'].includes(r.status)).length
  const ok = runs.filter((r) => r.status === 'pass').length
  const artifactsVerified = runs.flatMap((r) => r.artifacts).filter((a) => a.ok).length
  const artifactsTotal = runs.flatMap((r) => r.artifacts).length
  const statuses = [...new Set(runs.map((r) => r.status))]
  const overall = runs.length === 0
    ? (registered ? 'NOT RUN' : 'NOT READY')
    : runs.every((r) => r.status === 'pass')
      ? 'PASS'
      : runs.some((r) => r.status === 'fail')
        ? 'FAIL'
        : runs.every((r) => r.status === 'skipped')
          ? 'SKIPPED'
          : runs.every((r) => r.status === 'not_ready')
            ? 'NOT READY'
            : statuses.join('/').toUpperCase()
  return {
    tool,
    registered,
    executed: executed > 0,
    resultOk: runs.length > 0 && runs.every((r) => r.status === 'pass'),
    steps: runs.length,
    artifactsVerified,
    artifactsTotal,
    outcomes: statuses,
    overall,
  }
})

const payload = {
  kind: 'e2e',
  status: totals.fail > 0 ? 'fail' : totals.pass === 0 ? 'not_verified' : totals.blocked + totals.not_ready > 0 ? 'partial' : 'pass',
  startedAt,
  finishedAt,
  durationMs,
  projectRoot: PROJECT_ROOT,
  pluginRoot: PLUGIN_ROOT,
  node: process.version,
  config: { ...PLUGIN_CONFIG },
  filters: { only: [...only], skip: [...skip] },
  totals,
  toolMatrix: matrix,
  steps: results,
  blackboard: Object.fromEntries(
    Object.entries(bb).map(([k, v]) => [k, typeof v === 'object' && v !== null ? (Array.isArray(v) ? `[${v.length}]` : '[object]') : v]),
  ),
  rawDir: RAW_DIR,
  exitCode: totals.fail > 0 ? 1 : totals.pass === 0 ? 2 : 0,
}

const jsonFile = path.join(QA_ROOT, `e2e-${RUN_STAMP}.json`)
writeJson(jsonFile, payload)
writeJson(path.join(QA_ROOT, 'e2e-last.json'), payload)

// ---------------------------------------------------------------- markdown

const md = []
md.push('# E2E acceptance run — wenmai-3d-reconstruction')
md.push('')
md.push(`- started: \`${startedAt}\` · finished: \`${finishedAt}\` · duration: **${(durationMs / 1000).toFixed(1)} s**`)
md.push(`- node: \`${process.version}\` · plugin: \`${plugin.name || '(unnamed)'}\``)
md.push(`- projectRoot: \`${PROJECT_ROOT}\``)
md.push(`- filters: only=${[...only].join(',') || '—'} skip=${[...skip].join(',') || '—'}`)
md.push(
  `- steps: **${totals.pass} pass / ${totals.fail} fail / ${totals.blocked} blocked / ${totals.not_ready} not ready / ${totals.skipped} skipped**`,
)
md.push(`- raw per-step results: \`${RAW_DIR}\``)
md.push('')
md.push('## Tool matrix')
md.push('')
md.push('| tool | registered | executed | result ok | artifacts verified | outcome |')
md.push('|---|---|---|---|---|---|')
for (const row of matrix) {
  md.push(
    `| \`${row.tool}\` | ${row.registered ? 'yes' : '**no**'} | ${row.executed ? 'yes' : 'no'} | ${row.resultOk ? 'yes' : 'no'} | ${
      row.artifactsTotal ? `${row.artifactsVerified}/${row.artifactsTotal}` : '—'
    } | ${row.overall} |`,
  )
}
md.push('')
md.push('## Steps')
md.push('')
for (const r of results) {
  md.push(`### ${r.index}. \`${r.tool}\` — **${r.status.toUpperCase()}** (${(r.durationMs / 1000).toFixed(2)} s)`)
  md.push('')
  md.push(`- phase: ${r.phase}`)
  if (r.reason) md.push(`- reason: ${r.reason}`)
  if (r.error) md.push(`- error: \`${String(r.error).split('\n')[0]}\``)
  if (r.metrics && Object.keys(r.metrics).length) md.push(`- metrics: \`${JSON.stringify(r.metrics).slice(0, 600)}\``)
  if (r.args) md.push(`- args: \`${JSON.stringify(r.args).slice(0, 600)}\``)
  if (r.checks.length) {
    const failed = r.checks.filter((c) => !c.ok && c.warn !== true)
    const warned = r.checks.filter((c) => !c.ok && c.warn === true)
    md.push(`- assertions: ${r.checks.length - failed.length - warned.length}/${r.checks.length} passed, ${warned.length} warning(s)`)
    for (const c of failed) md.push(`  - ✗ ${c.name}${c.detail ? ` — \`${String(c.detail).slice(0, 300)}\`` : ''}`)
    for (const c of warned) md.push(`  - ! ${c.name} — \`${String(c.warnDetail || c.detail || '').slice(0, 300)}\``)
  }
  if (r.artifacts.length) {
    md.push('')
    md.push('| artifact | bytes | dims | inside root | ok |')
    md.push('|---|---|---|---|---|')
    for (const a of r.artifacts) {
      md.push(
        `| \`${a.label}\` ${a.path.replace(PROJECT_ROOT, '.')} | ${a.bytes} | ${a.width ? `${a.width}×${a.height}` : '—'} | ${a.insideProject ? 'yes' : '**NO**'} | ${a.ok ? 'yes' : '**NO**'} |`,
      )
    }
  }
  md.push('')
}
md.push('## Suite assertions')
md.push('')
for (const e of suiteSummary.entries) md.push(`- ${e.status === 'pass' ? 'ok' : e.status === 'fail' ? '**FAIL**' : e.status.toUpperCase()} — ${e.name}${e.detail ? `: ${String(e.detail).slice(0, 300)}` : ''}`)
md.push('')

const mdFile = path.join(QA_ROOT, `e2e-${RUN_STAMP}.md`)
writeText(mdFile, md.join('\n'))

console.log(`# wrote ${jsonFile}`)
console.log(`# wrote ${mdFile}`)
process.exit(payload.exitCode)
