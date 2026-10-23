/**
 * Module A — multi-view reconstruction tools.
 *
 *   wm_analyze_references  (Blender/numpy) deterministic measurements of the ten refs
 *   wm_build_scene_spec    (Node) merge observations + measurements into one spec
 *   wm_match_camera        (Blender/numpy) pinhole solve from 3D↔pixel correspondences
 *   wm_validate_multiview  (Blender/numpy) reproject the spec into every reference view
 */
import { existsSync, readdirSync } from 'node:fs'
import path from 'node:path'
import type { JsonValue, ToolDefinition } from '../lib/sdk.js'
import type { ResolvedConfig } from '../lib/config.js'
import { requireProjectFile, resolveInsideProject, resolveOutputDir, type PathViolation } from '../lib/config.js'
import { runBlenderTask } from '../lib/blender.js'
import { defineBankTool } from '../lib/tool.js'
import { buildSceneSpec, readJsonFile, type Observations } from '../lib/spec.js'
import { makeLocalResult, writeJsonArtifact } from '../lib/result.js'

type Args = Record<string, JsonValue>

function asString(args: Args, key: string): string | undefined {
  const value = args[key]
  if (value === undefined || value === null) return undefined
  if (typeof value !== 'string') throw new Error(`parameter "${key}" must be a string`)
  return value
}

function asNumber(args: Args, key: string): number | undefined {
  const value = args[key]
  if (value === undefined || value === null) return undefined
  if (typeof value !== 'number' || !Number.isFinite(value)) throw new Error(`parameter "${key}" must be a number`)
  return value
}

function asBool(args: Args, key: string): boolean | undefined {
  const value = args[key]
  if (value === undefined || value === null) return undefined
  if (typeof value !== 'boolean') throw new Error(`parameter "${key}" must be a boolean`)
  return value
}

function asObject(args: Args, key: string): Record<string, JsonValue> | undefined {
  const value = args[key]
  if (value === undefined || value === null) return undefined
  if (typeof value !== 'object' || Array.isArray(value)) throw new Error(`parameter "${key}" must be an object`)
  return value as Record<string, JsonValue>
}

function asStringArray(args: Args, key: string): string[] | undefined {
  const value = args[key]
  if (value === undefined || value === null) return undefined
  if (!Array.isArray(value) || value.some((item) => typeof item !== 'string')) {
    throw new Error(`parameter "${key}" must be an array of strings`)
  }
  return value as string[]
}

function listReferenceImages(cfg: ResolvedConfig): string[] {
  if (!existsSync(cfg.referencesDir)) {
    throw new Error(`references directory not found: ${cfg.referencesDir}`)
  }
  return readdirSync(cfg.referencesDir)
    .filter((name) => /\.(png|jpe?g)$/i.test(name))
    .sort()
    .map((name) => path.join(cfg.referencesDir, name))
}

/** Human-readable, stable view ids for the ten reference images (R01..R10). */
function referenceId(index: number): string {
  return `R${String(index + 1).padStart(2, '0')}`
}

/** Locate the measurements file produced by wm_analyze_references. */
function findMeasurements(cfg: ResolvedConfig, explicit?: string): string | null {
  const candidates = [
    explicit,
    path.join(cfg.reportsDir, 'analysis', 'measurements.json'),
    path.join(cfg.reportsDir, 'measurements.json'),
    path.join(cfg.workRoot, 'analysis', 'measurements.json'),
  ].filter((value): value is string => Boolean(value))
  for (const candidate of candidates) {
    const resolved = path.isAbsolute(candidate) ? path.resolve(candidate) : path.resolve(cfg.projectRoot, candidate)
    if (existsSync(resolved)) return resolved
  }
  return null
}

export function referenceTools(cfg: ResolvedConfig): ToolDefinition[] {
  const analyze = defineBankTool({
    name: 'wm_analyze_references',
    description:
      'Measure the ten heritage-gallery concept images without a vision model: exact size, palette, foreground silhouette box, ' +
      'roof/facade/plinth band ratios, edge density, gradient orientation per band (parallel vs radial tile courses), symmetry. ' +
      'Writes measurements.json plus a contact sheet. Evidence is numeric; it never claims to "see" the architecture.',
    parameters: {
      images: {
        type: 'array',
        items: { type: 'string' },
        description: 'Reference image paths inside the project (default: every PNG in assets/gallery3d/references/raw, sorted)',
      },
      outDir: { type: 'string', description: 'Output directory inside the project (default: outputs/wenmai-3d/reports/analysis)' },
      makeContactSheet: { type: 'boolean', description: 'Render a contact sheet PNG (default true)' },
    },
    renderTitle: 'Reference analysis',
    isConcurrencySafe: true,
    execute: async (raw) => {
      const args = raw as Args
      const inputImages = asStringArray(args, 'images')
      const images = inputImages
        ? inputImages.map((item, index) => {
            const resolved = requireProjectFile(cfg, item, `images[${index}]`)
            if (!/\.(png|jpe?g)$/i.test(resolved)) throw new Error(`images[${index}] is not a PNG/JPEG: ${resolved}`)
            return resolved
          })
        : listReferenceImages(cfg)
      if (images.length === 0) throw new Error('no reference images found')
      const outDir = resolveOutputDir(cfg, asString(args, 'outDir'), path.join(cfg.reportsDir, 'analysis'))
      const result = await runBlenderTask(cfg, 'analyze_references', {
        images,
        imageIds: images.map((image, index) => (inputImages ? path.basename(image, path.extname(image)) : referenceId(index))),
        outDir,
        makeContactSheet: asBool(args, 'makeContactSheet') ?? true,
      })
      return {
        ...result,
        images: result.images ?? [],
        measurementsPath: result.measurementsPath ?? null,
      } as unknown as JsonValue
    },
  })

  const buildSpec = defineBankTool({
    name: 'wm_build_scene_spec',
    description:
      'Merge the model\'s structured visual observations (components, sizes, confidence, per-image evidence) with the numeric ' +
      'measurements into one building spec JSON. Validates the envelope, enforces the v5 coordinate contract, records ' +
      'contradictions and unknowns instead of inventing dimensions.',
    parameters: {
      observations: {
        type: 'object',
        required: true,
        additionalProperties: true,
        description:
          'Visual observations: {sourceImages, envelope{baseSize,floor1Z,floor2Z,topZ,eaveZ,ridgeZ,footprintX,footprintZ}, ' +
          'components[{id,part,floor,shape,size,position,confidence,sourceImage}], constraints[], unknowns[], contradictions[]}',
      },
      measurementsPath: { type: 'string', description: 'Output of wm_analyze_references (auto-detected when omitted)' },
      outPath: { type: 'string', description: 'Spec output path (default: outputs/wenmai-3d/specs/scene_spec.json)' },
    },
    renderTitle: 'Building scene spec',
    isConcurrencySafe: true,
    execute: async (raw) => {
      const args = raw as Args
      const observations = asObject(args, 'observations')
      if (!observations) throw new Error('observations is required')
      const measurementsPath = findMeasurements(cfg, asString(args, 'measurementsPath'))
      const measurements = measurementsPath ? (readJsonFile(measurementsPath) as Record<string, unknown>) : null
      const explicitOut = asString(args, 'outPath')
      const outPath = explicitOut
        ? resolveInsideProject(cfg, explicitOut, 'outPath')
        : path.join(cfg.workRoot, 'specs', 'scene_spec.json')
      let built: ReturnType<typeof buildSceneSpec>
      try {
        built = buildSceneSpec({
          observations: observations as unknown as Observations,
          measurements,
          measurementsPath: measurementsPath ?? undefined,
          projectRoot: cfg.projectRoot,
          outPath,
        })
      } catch (error) {
        if ((error as PathViolation).name === 'PathViolation') throw error
        throw error
      }
      const checks = [
        {
          id: 'measurements_linked',
          status: measurementsPath ? 'pass' : 'warn',
          detail: measurementsPath ? `measurements: ${measurementsPath}` : 'no measurements file found; ratios unverified',
        },
        {
          id: 'envelope_monotonic',
          status: built.validation.floorsOrdered ? 'pass' : 'fail',
          detail: String(built.validation.floorsOrdered),
        },
        {
          id: 'contradictions',
          status: built.contradictions.length === 0 ? 'pass' : 'warn',
          detail: `${built.contradictions.length} contradiction(s) recorded`,
        },
        {
          id: 'frame_anchor_count',
          status: built.validation.frameAnchors === 0 || built.validation.frameAnchors === 15 ? 'pass' : 'warn',
          detail: `observations list ${String(built.validation.frameAnchors)} frame components (expected 15)`,
        },
      ]
      return makeLocalResult({
        task: 'build_scene_spec',
        projectRoot: cfg.projectRoot,
        artifacts: [{ kind: 'json', path: built.specPath }],
        checks,
        notes: 'Spec assembled from model observations + measured band ratios; defaults are labelled, not measured.',
        specPath: built.specPath,
        spec: built.spec as unknown as JsonValue,
        validation: built.validation,
        contradictions: built.contradictions as unknown as JsonValue,
        unknowns: built.unknowns,
        measurementsPath: measurementsPath ?? null,
      }) as unknown as JsonValue
    },
  })

  const matchCamera = defineBankTool({
    name: 'wm_match_camera',
    description:
      'Solve the reference camera: give ≥6 point correspondences (model 3D point ↔ reference pixel) and get a Blender camera ' +
      '(position, look-at target, lens mm, fov) whose reprojection error is reported per point. Writes camera.json.',
    parameters: {
      image: { type: 'string', required: true, description: 'Reference image the pixels belong to' },
      correspondences: {
        type: 'array',
        required: true,
        minItems: 6,
        description:
          'Array of {point3d:[x,y,z], pixel:[u,v]}; u,v in image pixels, origin top-left',
        items: {
          type: 'object',
          additionalProperties: false,
          properties: {
            point3d: { type: 'array', items: { type: 'number' }, minItems: 3, maxItems: 3 },
            pixel: { type: 'array', items: { type: 'number' }, minItems: 2, maxItems: 2 },
            label: { type: 'string' },
          },
        },
      },
      imageSize: { type: 'array', items: { type: 'integer' }, minItems: 2, maxItems: 2, description: '[width,height]' },
      init: { type: 'object', additionalProperties: true, description: 'Optional initial camera guess {distance,lens,yaw,pitch}' },
      outPath: { type: 'string', description: 'camera.json output path (default: outputs/wenmai-3d/specs/camera_<image>.json)' },
    },
    renderTitle: 'Camera match',
    isConcurrencySafe: true,
    execute: async (raw) => {
      const args = raw as Args
      const image = requireProjectFile(cfg, asString(args, 'image') ?? '', 'image')
      const correspondences = args.correspondences
      if (!Array.isArray(correspondences) || correspondences.length < 6) {
        throw new Error('correspondences must be an array with at least 6 {point3d,pixel} entries')
      }
      for (const [index, item] of correspondences.entries()) {
        const entry = item as Record<string, unknown>
        const p3 = entry?.point3d
        const p2 = entry?.pixel
        if (!Array.isArray(p3) || p3.length !== 3 || p3.some((v) => typeof v !== 'number')) {
          throw new Error(`correspondences[${index}].point3d must be [x,y,z] numbers`)
        }
        if (!Array.isArray(p2) || p2.length !== 2 || p2.some((v) => typeof v !== 'number')) {
          throw new Error(`correspondences[${index}].pixel must be [u,v] numbers`)
        }
      }
      const explicitOut = asString(args, 'outPath')
      const outPath = explicitOut
        ? resolveInsideProject(cfg, explicitOut, 'outPath')
        : path.join(cfg.workRoot, 'specs', `camera_${path.basename(image, path.extname(image)).slice(0, 40)}.json`)
      const result = await runBlenderTask(cfg, 'match_camera', {
        image,
        correspondences,
        imageSize: args.imageSize ?? null,
        init: asObject(args, 'init') ?? null,
        outPath,
      })
      return result as unknown as JsonValue
    },
  })

  const validateMultiview = defineBankTool({
    name: 'wm_validate_multiview',
    description:
      'Project the scene spec component boxes through the solved cameras into each reference image and report reprojection RMS ' +
      'plus per-component pixel offsets. Surfaces structural contradictions between the ten concept images.',
    parameters: {
      specPath: { type: 'string', description: 'scene_spec.json (default: outputs/wenmai-3d/specs/scene_spec.json)' },
      views: {
        type: 'array',
        description: 'Optional [{image, cameraPath}] pairs; defaults to every camera_*.json in the spec directory',
        items: {
          type: 'object',
          additionalProperties: false,
          properties: { image: { type: 'string' }, cameraPath: { type: 'string' } },
        },
      },
      outPath: { type: 'string', description: 'Report JSON path (default: outputs/wenmai-3d/reports/multiview_validation.json)' },
    },
    renderTitle: 'Multi-view validation',
    isConcurrencySafe: true,
    execute: async (raw) => {
      const args = raw as Args
      const explicitSpec = asString(args, 'specPath')
      const specPath = explicitSpec
        ? requireProjectFile(cfg, explicitSpec, 'specPath')
        : path.join(cfg.workRoot, 'specs', 'scene_spec.json')
      if (!existsSync(specPath)) throw new Error(`scene spec not found: ${specPath} (run wm_build_scene_spec first)`)
      const viewInput = args.views
      const views = Array.isArray(viewInput) ? viewInput : []
      const resolvedViews = views.map((item, index) => {
        const entry = item as Record<string, unknown>
        const image = typeof entry.image === 'string' ? requireProjectFile(cfg, entry.image, `views[${index}].image`) : ''
        const cameraPath = typeof entry.cameraPath === 'string' ? requireProjectFile(cfg, entry.cameraPath, `views[${index}].cameraPath`) : ''
        return { image, cameraPath }
      })
      const outPath = asString(args, 'outPath')
        ? resolveInsideProject(cfg, asString(args, 'outPath') as string, 'outPath')
        : path.join(cfg.reportsDir, 'multiview_validation.json')
      const result = await runBlenderTask(cfg, 'validate_multiview', {
        specPath,
        views: resolvedViews,
        outPath,
      })
      return result as unknown as JsonValue
    },
  })

  return [analyze, buildSpec, matchCamera, validateMultiview]
}

/** Exported for the e2e harness: deterministic reference ids. */
export function referenceIds(count: number): string[] {
  return Array.from({ length: count }, (_v, index) => referenceId(index))
}

/** Also exported so a spec writer can create a stub body without Blender. */
export function stubSpecPath(cfg: ResolvedConfig): string {
  const specPath = path.join(cfg.workRoot, 'specs', 'scene_spec.json')
  writeJsonArtifact(specPath, { schemaVersion: 1, note: 'stub' })
  return specPath
}
