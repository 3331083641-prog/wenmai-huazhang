/** Helpers for tools that compute in Node instead of driving Blender. */
import { mkdirSync, statSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import type { JsonValue } from './sdk.js'

export interface LocalResultInput {
  task: string
  artifacts?: Array<{ kind: string; path: string }>
  checks?: Array<Record<string, unknown>>
  warnings?: string[]
  notes?: string
  projectRoot: string
  [key: string]: unknown
}

/** Shape a Node-side computation exactly like a Blender task result. */
export function makeLocalResult(input: LocalResultInput): Record<string, unknown> {
  const { task, artifacts = [], checks = [], warnings = [], notes = '', projectRoot, ...rest } = input
  const shapedArtifacts = artifacts.map((artifact) => {
    let bytes = 0
    let exists = false
    try {
      exists = statSync(artifact.path).isFile()
      if (exists) bytes = statSync(artifact.path).size
    } catch {
      exists = false
    }
    const relative = path.relative(projectRoot, artifact.path).replace(/\\/g, '/')
    return { kind: artifact.kind, path: artifact.path, bytes, exists, relativePath: relative }
  })
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
    ...(rest as Record<string, JsonValue>),
  })
}

/** Recursively remove `undefined` members so the value stays lossless JSON. */
export function pruneUndefined<T>(value: T): T {
  if (Array.isArray(value)) {
    return value.filter((item) => item !== undefined).map((item) => pruneUndefined(item)) as unknown as T
  }
  if (value && typeof value === 'object') {
    const out: Record<string, unknown> = {}
    for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
      if (item === undefined) continue
      out[key] = pruneUndefined(item)
    }
    return out as unknown as T
  }
  return value
}

/** Write a JSON artifact and return its path. */
export function writeJsonArtifact(filePath: string, value: unknown): string {
  mkdirSync(path.dirname(filePath), { recursive: true })
  writeFileSync(filePath, JSON.stringify(value, null, 2), 'utf8')
  return filePath
}

/** Write a Markdown artifact and return its path. */
export function writeMarkdownArtifact(filePath: string, markdown: string): string {
  mkdirSync(path.dirname(filePath), { recursive: true })
  writeFileSync(filePath, markdown, 'utf8')
  return filePath
}
