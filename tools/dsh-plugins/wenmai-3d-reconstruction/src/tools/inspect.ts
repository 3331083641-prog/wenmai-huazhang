/**
 * Module D — automatic scene inspection tools (read-only).
 *
 * The inspector is explicit about epistemics: every check is pass / warn /
 * fail / manual / not_checked, and a browser-runtime problem that Blender
 * cannot see is never reported as passing.
 */
import { existsSync } from 'node:fs'
import path from 'node:path'
import type { JsonValue, ToolDefinition } from '../lib/sdk.js'
import type { ResolvedConfig } from '../lib/config.js'
import { requireProjectFile } from '../lib/config.js'
import { runBlenderTask } from '../lib/blender.js'
import { defineBankTool } from '../lib/tool.js'

type Args = Record<string, JsonValue>

function stringArg(args: Args, key: string): string | undefined {
  const value = args[key]
  if (value === undefined || value === null) return undefined
  if (typeof value !== 'string') throw new Error(`parameter "${key}" must be a string`)
  return value
}

function numberArg(args: Args, key: string): number | undefined {
  const value = args[key]
  if (value === undefined || value === null) return undefined
  if (typeof value !== 'number' || !Number.isFinite(value)) throw new Error(`parameter "${key}" must be a number`)
  return value
}

function resolveBlend(cfg: ResolvedConfig, args: Args): string {
  const explicit = stringArg(args, 'blend')
  if (explicit) return requireProjectFile(cfg, explicit, 'blend')
  const workScene = path.join(cfg.sceneDir, 'wenmai_scene.blend')
  if (existsSync(workScene)) return workScene
  return requireProjectFile(cfg, cfg.baseBlend, 'blend')
}

export function inspectTools(cfg: ResolvedConfig): ToolDefinition[] {
  const inspect = defineBankTool({
    name: 'wm_inspect_scene',
    description:
      'Audit the model: roof/beam intersections, roof surface holes, flipped normals, floating tiles, stair continuity, ' +
      'frame/wall and frame/window overlaps, bounds vs plinth, editable frame anchors, texture sizes. Reports honest statuses ' +
      'including manual/not_checked for anything only a browser can confirm.',
    parameters: {
      blend: { type: 'string', description: 'Blend to inspect (default: work scene, else the v5 model)' },
      checks: {
        type: 'array',
        items: { type: 'string' },
        description: 'Optional subset: roof_beams, roof_holes, normals, floating_tiles, stair, frames, bounds, textures',
      },
    },
    renderTitle: 'Scene inspection',
    isConcurrencySafe: true,
    execute: async (raw, exec) => {
      const args = raw as Args
      const blend = resolveBlend(cfg, args)
      const checks = Array.isArray(args.checks) ? (args.checks as string[]) : null
      const result = await runBlenderTask(cfg, 'inspect_scene', { blend, checks }, { baseBlend: blend, outBlend: blend, signal: exec.signal })
      return result as unknown as JsonValue
    },
  })

  const frames = defineBankTool({
    name: 'wm_check_art_frames',
    description:
      'Verify the 15 editable artwork anchors (FRAME_F1_001..007, FRAME_F2_001..008): exact ids, positions against ' +
      'gallery_layout.json, no duplicates, still empties (not joined into geometry), and not buried in walls.',
    parameters: {
      blend: { type: 'string', description: 'Blend to check (default: work scene, else the v5 model)' },
      expected: { type: 'integer', minimum: 1, maximum: 99, description: 'Expected frame count (default 15)' },
      layoutPath: { type: 'string', description: 'Layout JSON (default assets/gallery3d/exports/gallery_layout.json)' },
    },
    renderTitle: 'Artwork frames',
    isConcurrencySafe: true,
    execute: async (raw, exec) => {
      const args = raw as Args
      const blend = resolveBlend(cfg, args)
      const layoutInput = stringArg(args, 'layoutPath')
      const layoutPath = layoutInput
        ? requireProjectFile(cfg, layoutInput, 'layoutPath')
        : path.join(cfg.projectRoot, 'assets', 'gallery3d', 'exports', 'gallery_layout.json')
      const result = await runBlenderTask(
        cfg,
        'check_art_frames',
        { blend, expected: numberArg(args, 'expected') ?? 15, layoutPath },
        { baseBlend: blend, outBlend: blend, signal: exec.signal },
      )
      return result as unknown as JsonValue
    },
  })

  const checkExport = defineBankTool({
    name: 'wm_check_export',
    description:
      'Validate an exported GLB without external libraries: container header, JSON chunk, meshes/primitives, materials, ' +
      'embedded image dimensions, animations, file size. Reports whether Three.js-blocking problems exist.',
    parameters: {
      glb: { type: 'string', description: 'GLB path (default outputs/wenmai-3d/scene/wenmai_scene.glb)' },
      profile: { type: 'string', enum: ['web', 'general'], description: 'Validation profile (default web)' },
    },
    renderTitle: 'GLB validation',
    isConcurrencySafe: true,
    execute: async (raw, exec) => {
      const args = raw as Args
      const explicit = stringArg(args, 'glb')
      const glb = explicit
        ? requireProjectFile(cfg, explicit, 'glb')
        : requireProjectFile(cfg, path.join(cfg.sceneDir, 'wenmai_scene.glb'), 'glb')
      const result = await runBlenderTask(
        cfg,
        'check_export',
        { glb, profile: stringArg(args, 'profile') ?? 'web' },
        { signal: exec.signal },
      )
      return result as unknown as JsonValue
    },
  })

  const performance = defineBankTool({
    name: 'wm_performance_report',
    description:
      'Budget the web payload: mesh/triangle/material/texture totals, GLB size against a budget, and the heaviest hotspots ' +
      'with concrete recommendations (decimate, merge, texture downscale).',
    parameters: {
      blend: { type: 'string', description: 'Blend to measure (default: work scene, else the v5 model)' },
      glb: { type: 'string', description: 'GLB to measure (default outputs/wenmai-3d/scene/wenmai_scene.glb)' },
      triangleBudget: { type: 'integer', minimum: 1000, description: 'Triangle budget (default 350000)' },
      sizeBudgetMb: { type: 'number', minimum: 1, description: 'GLB size budget in MB (default 16)' },
    },
    renderTitle: 'Performance report',
    isConcurrencySafe: true,
    execute: async (raw, exec) => {
      const args = raw as Args
      const blend = resolveBlend(cfg, args)
      const explicitGlb = stringArg(args, 'glb')
      const glb = explicitGlb
        ? requireProjectFile(cfg, explicitGlb, 'glb')
        : path.join(cfg.sceneDir, 'wenmai_scene.glb')
      const result = await runBlenderTask(
        cfg,
        'performance_report',
        {
          blend,
          glb: existsSync(glb) ? glb : null,
          triangleBudget: numberArg(args, 'triangleBudget') ?? 350000,
          sizeBudgetMb: numberArg(args, 'sizeBudgetMb') ?? 16,
        },
        { baseBlend: blend, outBlend: blend, signal: exec.signal },
      )
      return result as unknown as JsonValue
    },
  })

  return [inspect, frames, checkExport, performance]
}
