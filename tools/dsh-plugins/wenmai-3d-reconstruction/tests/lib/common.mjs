/**
 * Shared harness kit for the wenmai-3d-reconstruction plugin tests.
 *
 * Owned by qa-harness. Nothing here imports the plugin's private modules; the
 * only plugin surface touched is the published one (`lib/index.js`) plus the
 * contract in `docs/CONTRACT.md`.
 *
 * Design rules:
 *  - a missing `lib/` build or a not-yet-written Python module is reported as
 *    `NOT READY`, never as a crash and never as a pass;
 *  - every assertion prints one TAP-ish line so the log alone is evidence;
 *  - exit codes: 0 all pass, 1 at least one failure, 2 nothing could be
 *    verified (build/module absent).
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

// --------------------------------------------------------------------- paths

export const HARNESS_DIR = path.dirname(fileURLToPath(import.meta.url)) // tests/lib
export const TESTS_DIR = path.dirname(HARNESS_DIR) // tests
export const PLUGIN_ROOT = path.dirname(TESTS_DIR) // plugin root
export const PLUGIN_LIB = path.join(PLUGIN_ROOT, 'lib')
export const PLUGIN_INDEX = path.join(PLUGIN_LIB, 'index.js')

export const PROJECT_ROOT = process.env.WM_PROJECT_ROOT || 'D:\\wenmai-huazhang'
export const OUTPUTS_ROOT =
  process.env.WM_OUTPUTS_ROOT || path.join(PROJECT_ROOT, 'outputs', 'wenmai-3d')
export const ARTIFACT_ROOT = path.join(OUTPUTS_ROOT, 'tests')
export const REFERENCES_DIR = path.join(PROJECT_ROOT, 'assets', 'gallery3d', 'references', 'raw')
export const BLENDER_EXE =
  process.env.WM_BLENDER ||
  'D:\\Codex\\blender-5.2.2\\blender-5.2.2-windows-x64\\blender.exe'

/** Plugin config used by the registration / e2e drivers. */
export const PLUGIN_CONFIG = {
  projectRoot: PROJECT_ROOT,
  blenderExe: BLENDER_EXE,
  timeoutMs: 20 * 60 * 1000,
  allowProjectWrites: true,
}

// ------------------------------------------------------------------- console

const USE_COLOR = process.env.NO_COLOR === undefined && process.stdout.isTTY
const paint = (code, s) => (USE_COLOR ? `\u001b[${code}m${s}\u001b[0m` : s)
export const c = {
  green: (s) => paint(32, s),
  red: (s) => paint(31, s),
  yellow: (s) => paint(33, s),
  cyan: (s) => paint(36, s),
  dim: (s) => paint(2, s),
  bold: (s) => paint(1, s),
}

/** Local timestamp, ISO-like, second precision (Asia/Shanghai host clock). */
export function stamp(date = new Date()) {
  const p = (n, w = 2) => String(n).padStart(w, '0')
  return (
    `${date.getFullYear()}-${p(date.getMonth() + 1)}-${p(date.getDate())}` +
    `T${p(date.getHours())}:${p(date.getMinutes())}:${p(date.getSeconds())}` +
    `${tzOffset(date)}`
  )
}

function tzOffset(d) {
  const m = -d.getTimezoneOffset()
  const sign = m >= 0 ? '+' : '-'
  const a = Math.abs(m)
  return `${sign}${String(Math.floor(a / 60)).padStart(2, '0')}:${String(a % 60).padStart(2, '0')}`
}

/** Filename-safe timestamp: 20261022-005112 */
export function fileStamp(date = new Date()) {
  const p = (n) => String(n).padStart(2, '0')
  return (
    `${date.getFullYear()}${p(date.getMonth() + 1)}${p(date.getDate())}-` +
    `${p(date.getHours())}${p(date.getMinutes())}${p(date.getSeconds())}`
  )
}

// ----------------------------------------------------------------- reporter

/**
 * TAP-ish reporter. Every test is one numbered line; failures carry a detail
 * block so the raw log is usable as acceptance evidence.
 */
export function createSuite(title, opts = {}) {
  const started = Date.now()
  const entries = []
  let n = 0
  const out = opts.stream || process.stdout

  const emit = (line) => out.write(line + '\n')

  emit(`TAP version 13`)
  emit(`# ${title} @ ${stamp()}`)
  emit(`# node ${process.version} · ${PLUGIN_ROOT}`)

  function record(status, name, detail) {
    n += 1
    const entry = { id: n, status, name, detail: detail === undefined ? undefined : String(detail) }
    entries.push(entry)
    return entry
  }

  const api = {
    ok(name, cond, detail) {
      if (cond) {
        record('pass', name)
        emit(`ok ${n} - ${name}`)
        return true
      }
      record('fail', name, detail || 'assertion failed')
      emit(`not ok ${n} - ${name}`)
      emit(`  ---`)
      emit(`  message: ${oneLine(detail || 'assertion failed')}`)
      emit(`  ...`)
      return false
    },

    eq(name, actual, expected) {
      const same = JSON.stringify(actual) === JSON.stringify(expected)
      return api.ok(
        name,
        same,
        same ? undefined : `expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`,
      )
    },

    /** Assert a thrown-error contract: fn must throw. */
    throws(name, fn) {
      try {
        fn()
      } catch (err) {
        record('pass', name)
        emit(`ok ${n} - ${name}`)
        return true
      }
      record('fail', name, 'expected the call to throw, it returned normally')
      emit(`not ok ${n} - ${name}`)
      emit(`  ---`)
      emit(`  message: expected throw`)
      emit(`  ...`)
      return false
    },

    fail(name, detail) {
      record('fail', name, detail)
      emit(`not ok ${n} - ${name}`)
      emit(`  ---`)
      emit(`  message: ${oneLine(detail)}`)
      emit(`  ...`)
    },

    /** Deliberately not exercised (e.g. excluded by --only). */
    skip(name, reason) {
      record('skip', name, reason)
      emit(`ok ${n} - ${name} # SKIP ${oneLine(reason)}`)
    },

    /**
     * Drift that is worth reporting but is not a hard failure — e.g. the
     * implementation renamed an optional contract parameter. Warnings never
     * turn the run green by themselves: ACCEPTANCE_EVIDENCE must list them.
     */
    warn(name, detail) {
      record('warn', name, detail)
      emit(`ok ${n} - ${name} # WARN ${oneLine(detail)}`)
    },

    /** Cannot run because an upstream artifact (build/Python module) is absent. */
    notReady(name, reason) {
      record('not_ready', name, reason)
      emit(`ok ${n} - ${name} # NOT-READY ${oneLine(reason)}`)
    },

    note(msg) {
      emit(`# ${msg}`)
    },

    get entries() {
      return entries
    },

    counts() {
      const k = { pass: 0, fail: 0, skip: 0, not_ready: 0, warn: 0 }
      for (const e of entries) k[e.status] += 1
      return k
    },

    summary() {
      const k = api.counts()
      const ms = Date.now() - started
      emit(`# tests ${n}`)
      emit(`# pass ${k.pass}`)
      emit(`# fail ${k.fail}`)
      emit(`# warn ${k.warn}`)
      emit(`# skip ${k.skip}`)
      emit(`# not ready ${k.not_ready}`)
      emit(`# duration ${ms}ms`)
      emit(`1..${n}`)
      // exit 1 when something genuinely failed; exit 2 when nothing ran.
      let exitCode = 0
      if (k.fail > 0) exitCode = 1
      else if (k.pass === 0 && k.warn === 0) exitCode = 2
      if (exitCode === 0) emit(c.green(`# PASS (${k.pass} checks, ${k.warn} warning(s), ${ms}ms)`))
      else if (exitCode === 1) emit(c.red(`# FAIL (${k.fail} failed, ${k.pass} passed, ${k.warn} warned, ${ms}ms)`))
      else emit(c.yellow(`# NOT VERIFIED (0 passed, ${k.not_ready} not ready, ${ms}ms)`))
      return { exitCode, ...k, durationMs: ms, entries }
    },
  }
  return api
}

function oneLine(s) {
  return String(s === undefined ? '' : s)
    .replace(/\r?\n/g, ' ⏎ ')
    .slice(0, 900)
}

// ------------------------------------------------------------------ loading

/**
 * Load the compiled plugin entry. Returns `{ok:false, missing:true}` when the
 * Lead's build has not produced `lib/index.js` yet — callers must report
 * NOT READY, not fail.
 */
export async function loadPlugin() {
  if (!fs.existsSync(PLUGIN_INDEX)) {
    return {
      ok: false,
      missing: true,
      reason: `lib/index.js missing (${PLUGIN_INDEX}) — run the tsc build first`,
    }
  }
  try {
    // cache-bust so a rebuilt lib/ is picked up in the same process family
    const mod = await import(`${pathToUrl(PLUGIN_INDEX)}?t=${Date.now()}`)
    return { ok: true, mod, namespace: mod.default }
  } catch (err) {
    return { ok: false, missing: false, reason: `import failed: ${err && err.message}`, error: err }
  }
}

export function pathToUrl(p) {
  return 'file:///' + p.replace(/\\/g, '/')
}

/** The effective plugin object: either the namespace itself or `default`. */
export function pluginObject(mod) {
  if (!mod) return undefined
  if (typeof mod.apply === 'function' || 'inject' in mod || 'name' in mod) return mod
  const def = mod.default
  if (def && (typeof def.apply === 'function' || typeof def === 'function' || 'inject' in def)) return def
  return mod
}

/**
 * List every compiled module under lib/ except the entry point — both the
 * helper modules (lib/lib/*.js) and the tool banks (lib/tools/*.js), so the unit
 * checks can reach a pure helper wherever the Lead put it.
 */
export function listLibModules() {
  if (!fs.existsSync(PLUGIN_LIB)) return []
  const found = []
  const walk = (d, depth = 0) => {
    if (depth > 4) return
    for (const ent of fs.readdirSync(d, { withFileTypes: true })) {
      const full = path.join(d, ent.name)
      if (ent.isDirectory()) {
        if (ent.name === 'types') continue
        walk(full, depth + 1)
      } else if (ent.isFile() && ent.name.endsWith('.js') && full !== PLUGIN_INDEX) {
        found.push(full)
      }
    }
  }
  walk(PLUGIN_LIB)
  return found.sort()
}

/**
 * Import every helper module and return `{module, file, exports}`.
 * A module that throws on import is reported instead of crashing the run.
 */
export async function loadHelperModules() {
  const out = []
  for (const file of listLibModules()) {
    try {
      const mod = await import(`${pathToUrl(file)}?t=${Date.now()}`)
      out.push({ file: path.relative(PLUGIN_LIB, file), mod, error: null })
    } catch (err) {
      out.push({ file: path.relative(PLUGIN_LIB, file), mod: null, error: String(err && err.message) })
    }
  }
  return out
}

/** Every function exported anywhere under lib/lib, with its origin module. */
export function collectFunctions(modules) {
  const fns = []
  for (const m of modules) {
    if (!m.mod) continue
    for (const [name, value] of Object.entries(m.mod)) {
      if (typeof value === 'function') fns.push({ name, fn: value, file: m.file })
    }
  }
  return fns
}

// ------------------------------------------------------------- fake context

/**
 * Minimal Cordis-shaped context. The registry only needs `register`, and the
 * plugin only ever touches `ctx.tools`, `ctx.logger` and (optionally) `ctx.get`
 * / `ctx.on`.
 */
export function createFakeContext() {
  const tools = []
  const byName = new Map()
  const logs = []
  const disposers = []

  const record = (level) => (...args) => {
    logs.push({ level, args: args.map((a) => (typeof a === 'string' ? a : safeJson(a))) })
  }

  const ctx = {
    tools: {
      register(def) {
        if (!def || typeof def.name !== 'string') {
          throw new Error('tools.register called without a named definition')
        }
        tools.push(def)
        byName.set(def.name, def)
        const dispose = () => {
          const i = tools.indexOf(def)
          if (i >= 0) tools.splice(i, 1)
          byName.delete(def.name)
        }
        disposers.push(dispose)
        return dispose
      },
      // Some host versions expose a lookup as well; harmless if unused.
      get(name) {
        return byName.get(name)
      },
    },
    logger: () => ({
      info: record('info'),
      warn: record('warn'),
      error: record('error'),
      debug: record('debug'),
    }),
    get: () => undefined,
    on: () => () => {},
    effect: (fn) => {
      const r = typeof fn === 'function' ? fn() : undefined
      return () => {
        if (typeof r === 'function') r()
      }
    },
  }

  return { ctx, tools, byName, logs, disposers }
}

function safeJson(v) {
  try {
    return JSON.stringify(v)
  } catch {
    return String(v)
  }
}

/** Run `apply(ctx, config)` and normalise the many shapes a plugin may return. */
export async function applyPlugin(plugin, ctx, config) {
  const fn = typeof plugin === 'function' ? plugin : plugin && plugin.apply
  if (typeof fn !== 'function') throw new Error('plugin has no apply() export')
  const result = await fn(ctx, config)
  // A { apply } / factory object result is acceptable; a ctx with tools is not.
  return result
}

// ------------------------------------------------------------- json schemas

const SCHEMA_TYPES = new Set(['string', 'number', 'integer', 'boolean', 'null', 'array', 'object'])

/**
 * Validate an object-rooted raw JSON Schema as the tool registry expects it.
 * Returns an array of human-readable problems (empty = valid).
 */
export function validateToolSchema(schema, label = 'schema') {
  const problems = []
  if (!schema || typeof schema !== 'object' || Array.isArray(schema)) {
    return [`${label}: not an object`]
  }
  if (schema.type !== 'object') problems.push(`${label}: root type must be "object", got ${JSON.stringify(schema.type)}`)
  if (!schema.properties || typeof schema.properties !== 'object' || Array.isArray(schema.properties)) {
    problems.push(`${label}: missing "properties" object`)
  }
  const props = schema.properties && typeof schema.properties === 'object' ? schema.properties : {}
  if (schema.required !== undefined) {
    if (!Array.isArray(schema.required)) problems.push(`${label}.required: must be an array`)
    else {
      for (const key of schema.required) {
        if (typeof key !== 'string') problems.push(`${label}.required: non-string entry ${JSON.stringify(key)}`)
        else if (!(key in props)) problems.push(`${label}.required: "${key}" is not declared in properties`)
      }
      const dupes = schema.required.filter((k, i) => schema.required.indexOf(k) !== i)
      if (dupes.length) problems.push(`${label}.required: duplicate entries ${JSON.stringify(dupes)}`)
    }
  }
  if (
    schema.additionalProperties !== undefined &&
    typeof schema.additionalProperties !== 'boolean' &&
    typeof schema.additionalProperties !== 'object'
  ) {
    problems.push(`${label}.additionalProperties: must be boolean or schema`)
  }
  for (const [key, value] of Object.entries(props)) {
    problems.push(...validateSchemaNode(value, `${label}.properties.${key}`, 0))
  }
  return problems
}

function validateSchemaNode(node, label, depth) {
  const problems = []
  if (depth > 6) return [`${label}: nested too deep`]
  if (!node || typeof node !== 'object' || Array.isArray(node)) return [`${label}: not an object`]

  const hasComp = node.oneOf || node.anyOf || node.allOf
  if (node.type !== undefined) {
    if (!SCHEMA_TYPES.has(node.type)) problems.push(`${label}.type: unsupported ${JSON.stringify(node.type)}`)
  } else if (!hasComp && node.enum === undefined && node.const === undefined) {
    problems.push(`${label}: no "type", and no enum/const/oneOf/anyOf`)
  }
  if (node.enum !== undefined) {
    if (!Array.isArray(node.enum) || node.enum.length === 0) problems.push(`${label}.enum: must be a non-empty array`)
  }
  if (node.type === 'array') {
    if (!node.items) problems.push(`${label}: array without "items"`)
    else problems.push(...validateSchemaNode(node.items, `${label}.items`, depth + 1))
  }
  for (const comb of ['oneOf', 'anyOf', 'allOf']) {
    if (node[comb] === undefined) continue
    if (!Array.isArray(node[comb]) || node[comb].length === 0) {
      problems.push(`${label}.${comb}: must be a non-empty array`)
      continue
    }
    node[comb].forEach((sub, i) => problems.push(...validateSchemaNode(sub, `${label}.${comb}[${i}]`, depth + 1)))
  }
  if (node.properties !== undefined) {
    if (typeof node.properties !== 'object' || Array.isArray(node.properties)) {
      problems.push(`${label}.properties: must be an object`)
    } else {
      for (const [k, v] of Object.entries(node.properties)) {
        problems.push(...validateSchemaNode(v, `${label}.properties.${k}`, depth + 1))
      }
    }
  }
  if (node.required !== undefined) {
    if (!Array.isArray(node.required)) problems.push(`${label}.required: must be an array`)
    else {
      const props = node.properties || {}
      for (const k of node.required) {
        if (!(k in props)) problems.push(`${label}.required: "${k}" not declared in nested properties`)
      }
    }
  }
  return problems
}

/** Shallow structural validation of an arbitrary JSON value against a schema. */
export function checkValueAgainstSchema(value, schema, label = 'value') {
  const problems = []
  if (!schema || typeof schema !== 'object') return problems
  const t = schema.type
  if (t === 'object') {
    if (value === null || typeof value !== 'object' || Array.isArray(value)) {
      return [`${label}: expected object, got ${typeName(value)}`]
    }
    for (const key of schema.required || []) {
      if (!(key in value)) problems.push(`${label}: missing required "${key}"`)
    }
    for (const [key, sub] of Object.entries(schema.properties || {})) {
      if (key in value) problems.push(...checkValueAgainstSchema(value[key], sub, `${label}.${key}`))
    }
  } else if (t === 'array') {
    if (!Array.isArray(value)) return [`${label}: expected array, got ${typeName(value)}`]
    value.forEach((v, i) => problems.push(...checkValueAgainstSchema(v, schema.items, `${label}[${i}]`)))
  } else if (t === 'string') {
    if (typeof value !== 'string') problems.push(`${label}: expected string, got ${typeName(value)}`)
  } else if (t === 'number') {
    if (typeof value !== 'number' || Number.isNaN(value)) problems.push(`${label}: expected number, got ${typeName(value)}`)
  } else if (t === 'integer') {
    if (!Number.isInteger(value)) problems.push(`${label}: expected integer, got ${typeName(value)}`)
  } else if (t === 'boolean') {
    if (typeof value !== 'boolean') problems.push(`${label}: expected boolean, got ${typeName(value)}`)
  }
  return problems
}

export function typeName(v) {
  if (v === null) return 'null'
  if (Array.isArray(v)) return 'array'
  return typeof v
}

// --------------------------------------------------------------- artifacts

/** Stat a path without throwing. */
export function statFile(p) {
  try {
    const st = fs.statSync(p)
    return { exists: true, isFile: st.isFile(), isDirectory: st.isDirectory(), bytes: st.size, mtime: st.mtimeMs }
  } catch {
    return { exists: false, isFile: false, isDirectory: false, bytes: 0, mtime: 0 }
  }
}

/** Read PNG IHDR dimensions from the first 33 bytes. */
export function readPngSize(file) {
  let fd
  try {
    fd = fs.openSync(file, 'r')
    const buf = Buffer.alloc(33)
    const read = fs.readSync(fd, buf, 0, 33, 0)
    if (read < 24) return null
    const sig = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]
    for (let i = 0; i < 8; i += 1) if (buf[i] !== sig[i]) return null
    if (buf.toString('ascii', 12, 16) !== 'IHDR') return null
    return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) }
  } catch {
    return null
  } finally {
    if (fd !== undefined) fs.closeSync(fd)
  }
}

/** Minimal baseline-JPEG SOF scan for dimensions. */
export function readJpegSize(file) {
  let buf
  try {
    buf = fs.readFileSync(file)
  } catch {
    return null
  }
  if (buf.length < 4 || buf[0] !== 0xff || buf[1] !== 0xd8) return null
  let off = 2
  while (off + 9 < buf.length) {
    if (buf[off] !== 0xff) {
      off += 1
      continue
    }
    const marker = buf[off + 1]
    if (marker === 0xd8 || marker === 0x01 || (marker >= 0xd0 && marker <= 0xd7)) {
      off += 2
      continue
    }
    const len = buf.readUInt16BE(off + 2)
    if (marker >= 0xc0 && marker <= 0xcf && marker !== 0xc4 && marker !== 0xc8 && marker !== 0xcc) {
      return { height: buf.readUInt16BE(off + 5), width: buf.readUInt16BE(off + 7) }
    }
    off += 2 + len
  }
  return null
}

export function readImageSize(file) {
  const ext = path.extname(file).toLowerCase()
  if (ext === '.png') return readPngSize(file)
  if (ext === '.jpg' || ext === '.jpeg') return readJpegSize(file)
  return null
}

export function looksLikeImage(p) {
  return ['.png', '.jpg', '.jpeg', '.webp'].includes(path.extname(String(p)).toLowerCase())
}

/**
 * Verify one artifact path: exists, is a file, size > 0, and — when the
 * extension says it is an image — that its header parses to positive size.
 */
export function verifyArtifact(p, opts = {}) {
  const minBytes = opts.minBytes === undefined ? 1 : opts.minBytes
  const out = { path: String(p), kind: path.extname(String(p)).slice(1) || 'unknown', ok: false, problems: [] }
  if (!p || typeof p !== 'string') {
    out.problems.push('empty artifact path')
    return out
  }
  const st = statFile(p)
  out.bytes = st.bytes
  if (!st.exists) {
    out.problems.push('missing on disk')
    return out
  }
  if (!st.isFile) {
    out.problems.push('not a regular file')
    return out
  }
  if (st.bytes <= minBytes - 1) out.problems.push(`size ${st.bytes} <= ${minBytes - 1}`)
  if (looksLikeImage(p)) {
    const size = readImageSize(p)
    if (!size) out.problems.push('image header unreadable')
    else {
      out.width = size.width
      out.height = size.height
      if (!(size.width > 0 && size.height > 0)) out.problems.push(`bad image dims ${size.width}x${size.height}`)
    }
  }
  out.ok = out.problems.length === 0
  return out
}

/**
 * Pull every artifact-ish path out of a tool result, following the shapes in
 * CONTRACT §2/§4: `artifacts[].path`, plus named single-path fields.
 */
const NAMED_PATH_FIELDS = [
  'glbPath',
  'copiedTo',
  'measurementsPath',
  'specPath',
  'cameraPath',
  'camerasPath',
  'sideBySide',
  'overlay',
  'contour',
  'reportPath',
  'outPath',
  'out',
]

export function collectArtifacts(result) {
  const found = []
  const seen = new Set()
  const push = (p, label) => {
    if (typeof p !== 'string' || !p) return
    if (seen.has(p)) return
    seen.add(p)
    found.push({ path: p, label })
  }
  if (!result || typeof result !== 'object') return found
  if (Array.isArray(result.artifacts)) {
    result.artifacts.forEach((a, i) => {
      if (a && typeof a === 'object') push(a.path, `artifacts[${i}]${a.kind ? `(${a.kind})` : ''}`)
      else if (typeof a === 'string') push(a, `artifacts[${i}]`)
    })
  }
  for (const f of NAMED_PATH_FIELDS) push(result[f], f)
  if (Array.isArray(result.shots)) result.shots.forEach((s, i) => s && push(s.path, `shots[${i}]${s.view ? `(${s.view})` : ''}`))
  if (Array.isArray(result.images)) {
    result.images.forEach((im, i) => im && push(typeof im === 'string' ? im : im.path, `images[${i}]`))
  }
  if (Array.isArray(result.perView)) result.perView.forEach((v, i) => v && push(v.image, `perView[${i}].image`))
  return found
}

/** Keep report files UTF-8 and newline-terminated. */
export function writeText(file, text) {
  fs.mkdirSync(path.dirname(file), { recursive: true })
  fs.writeFileSync(file, text.endsWith('\n') ? text : text + '\n', 'utf8')
  return file
}

// -------------------------------------------------------- activation log

/**
 * The plugin writes `outputs/wenmai-3d/logs/activation.json` on every mount,
 * overwriting the previous record. A headless harness run therefore destroys the
 * proof of a real host mount, so copy the existing file aside *before* mounting
 * and keep this run's own record afterwards.
 */
export const ACTIVATION_FILE = path.join(OUTPUTS_ROOT, 'logs', 'activation.json')

export function preserveActivation(kind) {
  try {
    if (!fs.existsSync(ACTIVATION_FILE)) return null
    const dest = path.join(ARTIFACT_ROOT, `activation-preserved-${fileStamp()}-${kind}.json`)
    fs.mkdirSync(ARTIFACT_ROOT, { recursive: true })
    fs.copyFileSync(ACTIVATION_FILE, dest)
    return dest
  } catch {
    return null
  }
}

export function snapshotActivation(kind) {
  try {
    if (!fs.existsSync(ACTIVATION_FILE)) return null
    const dest = path.join(ARTIFACT_ROOT, `activation-${kind}-${fileStamp()}.json`)
    fs.mkdirSync(ARTIFACT_ROOT, { recursive: true })
    fs.copyFileSync(ACTIVATION_FILE, dest)
    return dest
  } catch {
    return null
  }
}

export function writeJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true })
  fs.writeFileSync(file, JSON.stringify(value, null, 2) + '\n', 'utf8')
  return file
}

// ---------------------------------------------------------- contract table

/**
 * CONTRACT.md §4 is the authority for tool names and parameter names.
 *
 * `params` = every parameter §4 documents (required or optional);
 * `required` = the ones §4 leaves without a `?` **and** the 2026-10-22 §4
 * amendment still treats as mandatory (the amendment makes `blend`/`glb`
 * optional with a documented fallback chain, so they are not listed here).
 * `requireAny` = documented either/or groups the schema cannot express.
 */
export const CONTRACT_TOOLS = [
  // A. reconstruction
  {
    name: 'wm_analyze_references',
    group: 'A',
    params: ['images', 'outDir'],
    required: [],
  },
  {
    name: 'wm_build_scene_spec',
    group: 'A',
    params: ['observations', 'measurementsPath', 'outPath'],
    required: ['observations'],
  },
  {
    name: 'wm_match_camera',
    group: 'A',
    params: ['image', 'correspondences', 'imageSize', 'init', 'outPath'],
    required: ['image', 'correspondences'],
  },
  {
    name: 'wm_validate_multiview',
    group: 'A',
    params: ['specPath', 'views'],
    required: [],
  },
  // B. generation
  {
    name: 'wm_generate_roof',
    group: 'B',
    params: [
      'baseBlend', 'outBlend', 'style', 'footprintX', 'footprintY', 'eaveZ', 'ridgeZ',
      'overhang', 'cornerLift', 'slopePower', 'ridgeHalf', 'tileRows', 'tileCover',
      'tileSegments', 'tileThickness', 'ridgeOrnament', 'detail',
    ],
    required: [],
  },
  {
    name: 'wm_generate_timber',
    group: 'B',
    params: [
      'baseBlend', 'outBlend', 'baysX', 'baysY', 'columnRadius', 'f1H', 'f2H',
      'dougongLevels', 'rafterSpacing', 'detail',
    ],
    required: [],
  },
  {
    name: 'wm_generate_interior',
    group: 'B',
    params: [
      'baseBlend', 'outBlend', 'voidX', 'voidY', 'corridorWidth', 'railingHeight',
      'stairWidth', 'stairRisers', 'displayWalls', 'ceilingStyle', 'lanterns', 'detail',
    ],
    required: [],
    note: '§4 amendment: stair is required by stairWidth + stairRisers',
  },
  {
    name: 'wm_generate_diorama',
    group: 'B',
    params: [
      'baseBlend', 'outBlend', 'baseSize', 'plinthHeight', 'frieze', 'medallion',
      'paving', 'props', 'detail',
    ],
    required: [],
  },
  {
    name: 'wm_export_glb',
    group: 'B',
    params: ['blend', 'out', 'copyTo', 'draco', 'yUp'],
    required: [],
    note: '§4 amendment: blend is optional with a documented fallback',
  },
  // C. visual matching
  {
    name: 'wm_capture_views',
    group: 'C',
    params: ['blend', 'views', 'camerasPath', 'width', 'height', 'samples'],
    required: [],
    note: '§4 amendment: engine dropped (EEVEE only), blend optional',
  },
  {
    name: 'wm_compare_reference',
    group: 'C',
    params: ['reference', 'render', 'outDir', 'align', 'cameraPath'],
    required: ['reference', 'render'],
  },
  {
    name: 'wm_generate_diff_report',
    group: 'C',
    params: ['comparisons', 'comparisonPaths', 'outDir', 'title'],
    required: [],
    requireAny: [['comparisons', 'comparisonPaths']],
    note: '§4 amendment: outDir (not outPath); comparisons xor comparisonPaths',
  },
  {
    name: 'wm_propose_geometry_changes',
    group: 'C',
    params: ['reportPath', 'comparisonPath', 'specPath', 'outDir'],
    required: [],
    requireAny: [['reportPath', 'comparisonPath']],
    note: '§4 amendment: no parameterCatalog',
  },
  // D. inspection
  {
    name: 'wm_inspect_scene',
    group: 'D',
    params: ['blend', 'checks'],
    required: [],
    note: '§4 amendment: blend optional with fallback',
  },
  {
    name: 'wm_check_art_frames',
    group: 'D',
    params: ['blend', 'expected', 'layoutPath'],
    required: [],
    note: '§4 amendment: blend optional with fallback',
  },
  {
    name: 'wm_check_export',
    group: 'D',
    params: ['glb', 'profile'],
    required: [],
    note: '§4 amendment: glb optional with fallback',
  },
  {
    name: 'wm_performance_report',
    group: 'D',
    params: ['blend', 'glb', 'triangleBudget', 'sizeBudgetMb'],
    required: [],
    requireAny: [['blend', 'glb']],
    note: '§4 amendment: triangleBudget + sizeBudgetMb replace budget',
  },
]

export const CONTRACT_TOOL_NAMES = CONTRACT_TOOLS.map((t) => t.name)

export function contractTool(name) {
  return CONTRACT_TOOLS.find((t) => t.name === name)
}

// ---------------------------------------------------------------- CLI args

/** Tiny `--key=value` / `--flag` parser (no deps). */
export function parseArgs(argv = process.argv.slice(2)) {
  const out = { _: [] }
  for (const raw of argv) {
    if (!raw.startsWith('--')) {
      out._.push(raw)
      continue
    }
    const body = raw.slice(2)
    const eq = body.indexOf('=')
    if (eq === -1) out[body] = true
    else out[body.slice(0, eq)] = body.slice(eq + 1)
  }
  return out
}

/** `--only=a,b` / `--skip=c` → Set of tool names (empty set = no filter). */
export function csvSet(value) {
  if (!value || value === true) return new Set()
  return new Set(
    String(value)
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean),
  )
}
