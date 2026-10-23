/**
 * wenmai-3d-reconstruction — a DeepSeek Harness (Cordis) plugin that gives the
 * 《纹脉华章》 project real 3D reconstruction tooling:
 *
 *   A. reference-image analysis → building spec → camera solve → multiview check
 *   B. parametric Blender generation (roof / timber / interior / diorama / GLB)
 *   C. real renders, reference comparison, diff reports, parameter proposals
 *   D. geometry / frame / export / performance audits
 *
 * Host contract: DSH 0.2.1-rc.2. This module deliberately has zero runtime
 * imports so the profile that loads it does not need a second copy of the
 * Cordis/dsh-tools runtime.
 */
import { appendFileSync, mkdirSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import type { PluginContext, PluginConfig } from './lib/sdk.js'
import { assertBlender, assertProjectRoot, resolveConfig } from './lib/config.js'
import { referenceTools } from './tools/references.js'
import { generateTools } from './tools/generate.js'
import { visualTools } from './tools/visual.js'
import { inspectTools } from './tools/inspect.js'

export const name = 'wenmai-3d-reconstruction'

/** Cordis service injection: tools must exist before registration. */
export const inject = ['tools']

/**
 * Register every wenmai tool on the host registry.
 *
 * @param ctx - Cordis context carrying `tools`.
 * @param config - plain JSON config from the profile patch.
 * @returns a disposer that unregisters exactly the tools this plugin added.
 */
export function apply(ctx: PluginContext, config?: PluginConfig): () => void {
  const cfg = resolveConfig(config)
  assertProjectRoot(cfg)
  assertBlender(cfg)
  for (const dir of [cfg.workRoot, cfg.jobsDir, cfg.sceneDir, cfg.rendersDir, cfg.reportsDir]) {
    mkdirSync(dir, { recursive: true })
  }

  const logger = ctx.logger?.('wenmai-3d')
  const disposers: Array<() => void> = []
  const definitions = [
    ...referenceTools(cfg),
    ...generateTools(cfg),
    ...visualTools(cfg),
    ...inspectTools(cfg),
  ]
  const seen = new Set<string>()
  for (const definition of definitions) {
    if (seen.has(definition.name)) throw new Error(`duplicate tool name: ${definition.name}`)
    seen.add(definition.name)
    disposers.push(ctx.tools.register(definition))
  }
  logger?.info?.(
    `registered ${definitions.length} tools (projectRoot=${cfg.projectRoot}, blender=${cfg.blenderExe})`,
  )
  // Activation record: the only in-process proof that the *host* (not a test
  // harness) mounted this plugin. `activation.json` is the latest mount and is
  // overwritten by every mount (including test harnesses), so the append-only
  // `activation-log.jsonl` is the durable history that a mount happened and
  // which process made it.
  try {
    const logDir = path.join(cfg.workRoot, 'logs')
    mkdirSync(logDir, { recursive: true })
    const record = {
      plugin: name,
      at: new Date().toISOString(),
      pid: process.pid,
      ppid: process.ppid,
      execPath: process.execPath,
      argv: process.argv.slice(0, 3),
      nodeVersion: process.version,
      tools: definitions.map((definition) => definition.name),
      projectRoot: cfg.projectRoot,
      blenderExe: cfg.blenderExe,
    }
    writeFileSync(path.join(logDir, 'activation.json'), JSON.stringify(record, null, 2), 'utf8')
    appendFileSync(path.join(logDir, 'activation-log.jsonl'), JSON.stringify(record) + '\n', 'utf8')
  } catch (error) {
    logger?.warn?.(`activation record failed: ${(error as Error).message}`)
  }

  return () => {
    for (const dispose of disposers.reverse()) {
      try {
        dispose()
      } catch (error) {
        logger?.warn?.(`tool dispose failed: ${(error as Error).message}`)
      }
    }
  }
}
