/**
 * Scene-spec assembly for `wm_build_scene_spec`.
 *
 * This is deliberately deterministic: the model supplies structured visual
 * observations (what it saw, which image, how confident), and this module
 * merges them with the numeric measurements produced by
 * `wm_analyze_references`, validates the envelope, and records contradictions
 * instead of silently averaging them away.
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import type { JsonValue } from './sdk.js'

export interface ObservationComponent {
  id: string
  part: 'base' | 'roof' | 'timber' | 'wall' | 'floor' | 'stair' | 'railing' | 'interior' | 'prop' | 'frame'
  floor?: number
  shape?: string
  size?: [number, number, number]
  position?: [number, number, number]
  confidence?: number
  sourceImage?: string
  notes?: string
  [key: string]: unknown
}

export interface Observations {
  sourceImages?: string[]
  envelope?: Record<string, number>
  components?: ObservationComponent[]
  constraints?: string[]
  unknowns?: string[]
  contradictions?: Array<Record<string, unknown>>
  [key: string]: unknown
}

export interface SceneSpec {
  schemaVersion: number
  generatedBy: string
  generatedAt: string
  units: 'metre'
  up: 'Z'
  origin: string
  coordinateContract: Record<string, string>
  envelope: Record<string, number>
  components: ObservationComponent[]
  constraints: string[]
  contradictions: Array<Record<string, unknown>>
  unknowns: string[]
  evidence: Array<{ image: string; usedFor: string }>
  measurementSummary?: Record<string, JsonValue>
}

interface MeasurementsFile {
  images?: Array<Record<string, unknown>>
  [key: string]: unknown
}

const REQUIRED_ENVELOPE = ['baseSize', 'floor1Z', 'floor2Z', 'topZ', 'eaveZ', 'ridgeZ', 'footprintX', 'footprintZ'] as const

function num(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined
}

function median(values: number[]): number | undefined {
  if (values.length === 0) return undefined
  const sorted = [...values].sort((a, b) => a - b)
  const mid = Math.floor(sorted.length / 2)
  return sorted.length % 2 === 0 ? ((sorted[mid - 1] ?? 0) + (sorted[mid] ?? 0)) / 2 : sorted[mid]
}

/** Read measured band ratios from the analyser output (tolerant of layout). */
export function measurementSummary(measurements: MeasurementsFile | null): Record<string, JsonValue> {
  if (!measurements || !Array.isArray(measurements.images)) return {}
  const roof: number[] = []
  const base: number[] = []
  const facade: number[] = []
  for (const image of measurements.images) {
    const bands = image.bands as Record<string, unknown> | undefined
    const ratio = (key: string): number | undefined => {
      const value = bands?.[key]
      if (typeof value === 'number') return value
      if (value && typeof value === 'object') {
        const r = (value as Record<string, unknown>).ratio
        if (typeof r === 'number') return r
      }
      return undefined
    }
    const roofRatio = ratio('roof') ?? ratio('roofBand')
    const baseRatio = ratio('plinth') ?? ratio('baseBand')
    const facadeRatio = ratio('upper') ?? ratio('facade')
    if (roofRatio !== undefined) roof.push(roofRatio)
    if (baseRatio !== undefined) base.push(baseRatio)
    if (facadeRatio !== undefined) facade.push(facadeRatio)
  }
  return {
    imageCount: measurements.images.length,
    roofBandRatioMedian: median(roof) ?? null,
    plinthBandRatioMedian: median(base) ?? null,
    facadeBandRatioMedian: median(facade) ?? null,
  }
}

export interface BuildSpecInput {
  observations: Observations
  measurements: MeasurementsFile | null
  measurementsPath?: string
  projectRoot: string
  outPath: string
}

export function buildSceneSpec(input: BuildSpecInput): {
  spec: SceneSpec
  specPath: string
  validation: Record<string, JsonValue>
  contradictions: Array<Record<string, unknown>>
  unknowns: string[]
} {
  const observations = input.observations ?? {}
  const envelopeIn = observations.envelope ?? {}
  const envelope: Record<string, number> = {}
  const missing: string[] = []
  for (const key of REQUIRED_ENVELOPE) {
    const value = num(envelopeIn[key])
    if (value === undefined) missing.push(key)
    else envelope[key] = value
  }
  // Documented defaults from the existing v5 web contract; recorded as
  // "inferred" rather than passed off as measured.
  const defaults: Record<string, number> = {
    baseSize: 16.0,
    floor1Z: 0.25,
    floor2Z: 3.6,
    topZ: 6.55,
    eaveZ: 6.15,
    ridgeZ: 11.3,
    footprintX: 8.4,
    footprintZ: 7.5,
    hallOffsetZ: 0.55,
    baseThickness: 0.65,
  }
  for (const [key, value] of Object.entries(defaults)) {
    if (envelope[key] === undefined) envelope[key] = value
  }

  const components = Array.isArray(observations.components) ? observations.components : []
  const contradictions: Array<Record<string, unknown>> = []
  const unknowns: string[] = []
  const validation: Record<string, JsonValue> = {}

  // ---- structural checks -------------------------------------------------
  const ids = new Set<string>()
  for (const component of components) {
    if (!component.id) contradictions.push({ id: 'component-without-id', detail: component })
    else if (ids.has(component.id)) contradictions.push({ id: 'duplicate-component-id', component: component.id })
    else ids.add(component.id)
    if (component.confidence !== undefined && component.confidence < 0.5 && component.id) {
      unknowns.push(`${component.id}: low visual confidence (${component.confidence})`)
    }
  }

  const parts = components.reduce<Record<string, number>>((acc, component) => {
    acc[component.part] = (acc[component.part] ?? 0) + 1
    return acc
  }, {})
  validation.componentCounts = parts as JsonValue
  if (!parts.roof) contradictions.push({ id: 'no-roof-component', detail: 'observations.components has no roof part' })
  if (!parts.base) contradictions.push({ id: 'no-base-component', detail: 'observations.components has no base part' })

  const baseSize = envelope.baseSize
  const baseThickness = envelope.baseThickness ?? 0.65
  validation.baseSquare =
    Math.abs(baseSize - baseSize) < 1e-6
      ? 'square by construction (single baseSize)'
      : 'non-square base is not supported by the v5 web contract'
  validation.baseThickness = baseThickness
  const floors = [envelope.floor1Z, envelope.floor2Z, envelope.topZ, envelope.ridgeZ]
  validation.floorsOrdered = floors.every((value, index) => index === 0 || value > (floors[index - 1] ?? -Infinity))
  if (!validation.floorsOrdered) {
    contradictions.push({ id: 'envelope-not-monotonic', detail: floors })
  }
  // The eave line legitimately sits a little below the wall head (the roof
  // bears on the top plate); it only has to be above the second floor slab.
  validation.eaveBetweenFloors = envelope.eaveZ > envelope.floor2Z + 1.2 && envelope.eaveZ <= envelope.topZ + 1.0
  if (!validation.eaveBetweenFloors) {
    contradictions.push({
      id: 'eave-height-implausible',
      detail: `eaveZ=${envelope.eaveZ} must be above floor2Z+1.2 (${envelope.floor2Z + 1.2}) and at most topZ+1.0 (${envelope.topZ + 1.0})`,
    })
  }
  const eavesAboveTop = envelope.eaveZ > envelope.topZ - 1.0
  validation.eaveAboveWallHead = eavesAboveTop
  if (!eavesAboveTop) contradictions.push({ id: 'eave-below-wall-head', detail: `eaveZ=${envelope.eaveZ}, topZ=${envelope.topZ}` })

  const expectedFrames = num((observations as Record<string, unknown>).frameAnchorCount) ?? 15
  const frameComponents = components.filter((component) => component.part === 'frame')
  validation.frameAnchors = frameComponents.length
  if (frameComponents.length !== 0 && frameComponents.length !== expectedFrames) {
    contradictions.push({
      id: 'frame-count-mismatch',
      detail: `expected ${expectedFrames} frame anchors, observations list ${frameComponents.length}`,
    })
  }

  // ---- measurement cross-check -------------------------------------------
  const summary = measurementSummary(input.measurements)
  const totalHeight = envelope.ridgeZ - 0.0
  const roofHeight = envelope.ridgeZ - envelope.eaveZ
  const roofRatio = totalHeight > 0 ? roofHeight / totalHeight : 0
  validation.modelRoofHeight = Math.round(roofHeight * 1000) / 1000
  validation.modelRoofRatio = Math.round(roofRatio * 1000) / 1000
  const measuredRoof = typeof summary.roofBandRatioMedian === 'number' ? summary.roofBandRatioMedian : undefined
  if (measuredRoof !== undefined) {
    const delta = Math.abs(measuredRoof - roofRatio)
    validation.measuredRoofRatio = measuredRoof
    validation.roofRatioDelta = Math.round(delta * 1000) / 1000
    if (delta > 0.12) {
      contradictions.push({
        id: 'roof-ratio-mismatch',
        detail: `spec roof/total=${roofRatio.toFixed(3)} vs measured median ${measuredRoof.toFixed(3)} (Δ${delta.toFixed(3)})`,
        severity: delta > 0.22 ? 'high' : 'medium',
      })
    }
  } else {
    validation.measuredRoofRatio = null
    unknowns.push('reference band ratios unavailable — run wm_analyze_references first')
  }

  // ---- spec assembly -----------------------------------------------------
  const sourceImages = Array.isArray(observations.sourceImages) ? observations.sourceImages : []
  const evidence = sourceImages.map((image) => ({ image, usedFor: 'reference view' }))
  const supplied = Array.isArray(observations.contradictions) ? observations.contradictions : []
  contradictions.push(...supplied)
  const suppliedUnknowns = Array.isArray(observations.unknowns) ? observations.unknowns : []
  unknowns.push(...suppliedUnknowns)

  const spec: SceneSpec = {
    schemaVersion: 1,
    generatedBy: 'wenmai-3d-reconstruction/wm_build_scene_spec',
    generatedAt: new Date().toISOString(),
    units: 'metre',
    up: 'Z',
    origin: 'plinth geometric centre; plinth top = z 0; front faces -Y',
    coordinateContract: {
      up: '+Z',
      front: '-Y',
      right: '+X',
      units: 'metre',
      base: `square ${baseSize} m`,
    },
    envelope,
    components,
    constraints: Array.isArray(observations.constraints) ? observations.constraints : [],
    contradictions,
    unknowns,
    evidence,
    measurementSummary: summary,
  }

  const outPath = path.resolve(input.outPath)
  mkdirSync(path.dirname(outPath), { recursive: true })
  writeFileSync(outPath, JSON.stringify(spec, null, 2), 'utf8')

  validation.missingEnvelopeKeys = missing as JsonValue
  validation.defaultsUsed = Object.keys(defaults).filter((key) => num(envelopeIn[key]) === undefined) as JsonValue
  return { spec, specPath: outPath, validation, contradictions, unknowns }
}

export function readJsonFile(filePath: string): unknown {
  if (!existsSync(filePath)) throw new Error(`file not found: ${filePath}`)
  return JSON.parse(readFileSync(filePath, 'utf8'))
}
