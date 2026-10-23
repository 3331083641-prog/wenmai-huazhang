#!/usr/bin/env node
/**
 * Unit checks for wenmai-3d-reconstruction's pure helpers and module surface.
 *
 *   node tests/run-unit.mjs [--strict]
 *
 * The plugin's compiled helpers are discovered by export name, so a renamed
 * module degrades to NOT READY instead of a crash — but every helper that *is*
 * found is asserted against the behaviour docs/CONTRACT.md promises:
 *
 *   config/paths  resolveConfig, resolveInsideProject, requireProjectFile,
 *                 resolveOutputDir  (project-root containment + PathViolation)
 *   job id        makeJobId  (CONTRACT §2: YYYYMMDD-HHMMSS-<task>-<suffix>)
 *   results       makeLocalResult / asTaskResult (CONTRACT §2 result shape)
 *   schema        compileParams (object-rooted registry schema)
 *   presentation  renderValue (bounded, status-aware content block)
 *
 * Exit codes: 0 = all pass · 1 = at least one failure · 2 = nothing verified.
 */

import fs from 'node:fs'
import path from 'node:path'
import {
  ARTIFACT_ROOT,
  checkValueAgainstSchema,
  collectFunctions,
  CONTRACT_TOOL_NAMES,
  contractTool,
  createSuite,
  fileStamp,
  loadHelperModules,
  loadPlugin,
  parseArgs,
  PLUGIN_CONFIG,
  PLUGIN_INDEX,
  PLUGIN_ROOT,
  pluginObject,
  PROJECT_ROOT,
  statFile,
  stamp,
  validateToolSchema,
  writeJson,
} from './lib/common.mjs'

const args = parseArgs()
const suite = createSuite('run-unit', {})

const evidence = {
  kind: 'unit',
  startedAt: stamp(),
  pluginRoot: PLUGIN_ROOT,
  libPresent: fs.existsSync(PLUGIN_INDEX),
  checks: [],
  discovered: {},
  exitCode: null,
}

// ------------------------------------------------------------ 1. manifest

suite.note('package manifest + bundle wiring')
let manifest = null
try {
  manifest = JSON.parse(fs.readFileSync(path.join(PLUGIN_ROOT, 'package.json'), 'utf8'))
} catch (err) {
  suite.fail('package.json parses', String(err && err.message))
}

if (manifest) {
  suite.ok('package.json parses', true)
  suite.eq('manifest name', manifest.name, 'wenmai-3d-reconstruction')
  suite.eq('manifest is ESM', manifest.type, 'module')
  suite.eq('manifest main points at lib/index.js', manifest.main, 'lib/index.js')
  const patchRel = manifest.dsh && manifest.dsh.bundle && manifest.dsh.bundle.patch
  suite.ok('package.json declares dsh.bundle.patch', typeof patchRel === 'string' && patchRel.length > 0, JSON.stringify(manifest.dsh))
  if (typeof patchRel === 'string') {
    const patchFile = path.resolve(PLUGIN_ROOT, patchRel)
    if (fs.existsSync(patchFile)) {
      const text = fs.readFileSync(patchFile, 'utf8')
      suite.ok('bundle patch file exists', true)
      suite.ok('bundle patch is a non-empty YAML list', /^-\s/m.test(text) || /^\s*\[\s*\]\s*$/m.test(text), `${text.length} bytes`)
      suite.ok('bundle patch references the plugin package', /wenmai-3d-reconstruction/.test(text), 'patch does not mention the package name')
      suite.ok('bundle patch row has an id', /id:\s*\S+/.test(text), 'no `id:` key found')
    } else {
      suite.notReady('bundle patch file exists', `${patchRel} not written yet (Lead owns cordis.patch.yml)`)
    }
  }
}

// --------------------------------------------------------- 2. entry exports

suite.note('plugin entry exports')
const loaded = await loadPlugin()
let plugin = null
let allFns = []

if (!loaded.ok) {
  suite.notReady('lib/index.js exists', loaded.reason)
  for (const n of ['exports name', 'exports inject', 'exports apply', 'helper discovery']) suite.notReady(n, loaded.reason)
} else {
  suite.ok('lib/index.js exists', true)
  const ns = loaded.mod
  plugin = pluginObject(ns)

  const name = plugin && plugin.name !== undefined ? plugin.name : ns.name
  suite.ok('exports name (non-empty string)', typeof name === 'string' && name.trim().length > 0, `got ${JSON.stringify(name)}`)
  const inject = plugin && plugin.inject
  const injectArr = Array.isArray(inject) ? inject : inject && Array.isArray(inject.required) ? inject.required : undefined
  suite.ok('exports inject (array)', Array.isArray(injectArr), `got ${JSON.stringify(inject)}`)
  if (Array.isArray(injectArr)) suite.ok("inject requires 'tools'", injectArr.includes('tools'), `inject = ${JSON.stringify(injectArr)}`)
  const apply = plugin && (plugin.apply || (typeof plugin === 'function' ? plugin : undefined))
  suite.ok('exports apply (function)', typeof apply === 'function', `got ${typeof apply}`)

  const helperModules = await loadHelperModules()
  for (const m of helperModules.filter((x) => x.error)) suite.fail(`helper module imports cleanly: ${m.file}`, m.error)
  const indexFns = Object.entries(ns)
    .filter(([, v]) => typeof v === 'function')
    .map(([n, v]) => ({ name: n, fn: v, file: 'index.js' }))
  allFns = [...indexFns, ...collectFunctions(helperModules)]

  evidence.discovered = {
    name,
    inject: injectArr,
    exportKeys: Object.keys(ns),
    modules: helperModules.map((m) => ({ file: m.file, exports: m.mod ? Object.keys(m.mod) : [], error: m.error })),
    functions: allFns.map((f) => `${f.file}#${f.name}`),
  }
  suite.ok('at least one helper module compiled', helperModules.length > 0, `lib/lib contains no .js modules`)
}

/** name → fn map across every compiled module (later modules win on collision). */
const FN = new Map()
for (const f of allFns) FN.set(f.name, f)

function pick(names) {
  for (const n of names) {
    const hit = FN.get(n)
    if (hit) return hit
  }
  return null
}

function section(title) {
  suite.note(title)
}

// ------------------------------------------------- 3. config + path safety

section('config resolution + path authorisation (CONTRACT §0: project root only)')
const resolveConfig = pick(['resolveConfig'])
const resolveInsideProject = pick(['resolveInsideProject'])
const PathViolationClass = pick(['PathViolation'])
const requireProjectFile = pick(['requireProjectFile'])
const resolveOutputDir = pick(['resolveOutputDir'])

let cfg = null
if (!loaded.ok) {
  suite.notReady('config resolution', loaded.reason)
} else if (!resolveConfig) {
  suite.notReady('resolveConfig', 'no exported resolveConfig found')
} else {
  try {
    cfg = resolveConfig.fn({ projectRoot: PROJECT_ROOT, blenderExe: PLUGIN_CONFIG.blenderExe, allowProjectWrites: true })
    suite.ok('resolveConfig returns an object', !!cfg && typeof cfg === 'object')
    suite.eq('resolveConfig honours projectRoot', cfg.projectRoot, PROJECT_ROOT)
    suite.ok(
      'workRoot is under <projectRoot>\\outputs\\wenmai-3d',
      typeof cfg.workRoot === 'string' && cfg.workRoot.toLowerCase().startsWith(path.join(PROJECT_ROOT, 'outputs', 'wenmai-3d').toLowerCase()),
      String(cfg.workRoot),
    )
    for (const key of ['jobsDir', 'sceneDir', 'rendersDir', 'reportsDir']) {
      suite.ok(
        `${key} is inside projectRoot`,
        typeof cfg[key] === 'string' && path.relative(PROJECT_ROOT, cfg[key]) && !path.relative(PROJECT_ROOT, cfg[key]).startsWith('..'),
        String(cfg[key]),
      )
    }
    suite.ok('referencesDir points at the reference folder', /references[\\/]raw$/i.test(cfg.referencesDir || ''), String(cfg.referencesDir))
    suite.ok('baseBlend points at the v5 scene', /wenmai_gallery_v5\.blend$/i.test(cfg.baseBlend || ''), String(cfg.baseBlend))
    suite.ok('blenderExe is absolute', path.isAbsolute(cfg.blenderExe || ''), String(cfg.blenderExe))
    // CONTRACT §6 (amended 2026-10-22): default Blender timeout 30 min = 1_800_000 ms.
    suite.eq('timeout default (CONTRACT §6: 30 min)', cfg.timeoutMs, 1800000)
    try {
      const contractText = fs.readFileSync(path.join(PLUGIN_ROOT, 'docs', 'CONTRACT.md'), 'utf8')
      const section6 = contractText.split(/^## 6\./m)[1] || contractText
      suite.ok(
        'CONTRACT §6 documents the same 1_800_000 ms default the code uses',
        /1_800_000/.test(section6),
        'docs/CONTRACT.md §6 does not mention 1_800_000 — code and contract disagree again',
      )
    } catch (err) {
      suite.notReady('CONTRACT §6 documents 1_800_000 ms', `could not read docs/CONTRACT.md: ${err.message}`)
    }

    const clampedLow = resolveConfig.fn({ projectRoot: PROJECT_ROOT, timeoutMs: 1 })
    suite.eq('timeout clamped to 30 s minimum', clampedLow.timeoutMs, 30000)
    const clampedHigh = resolveConfig.fn({ projectRoot: PROJECT_ROOT, timeoutMs: 99_999_999 })
    suite.eq('timeout clamped to 2 h maximum', clampedHigh.timeoutMs, 7200000)
    const defaulted = resolveConfig.fn(undefined)
    suite.eq('resolveConfig(undefined) falls back to the project default root', defaulted.projectRoot, 'D:\\wenmai-huazhang')
  } catch (err) {
    suite.fail('resolveConfig is callable', String(err && err.stack))
  }
}

if (!loaded.ok) {
  suite.notReady('path authorisation', loaded.reason)
} else if (!resolveInsideProject) {
  suite.notReady('resolveInsideProject', 'no exported resolveInsideProject found')
} else if (!cfg) {
  suite.notReady('path authorisation', 'config resolution failed, cannot build a ResolvedConfig')
} else {
  const call = (p) => resolveInsideProject.fn(cfg, p)
  const expectThrow = (label, p) => {
    try {
      const value = call(p)
      suite.fail(label, `expected PathViolation, got ${JSON.stringify(value)}`)
    } catch (err) {
      const isViolation =
        (PathViolationClass && err instanceof PathViolationClass.fn) || err.name === 'PathViolation'
      suite.ok(label, isViolation, `threw ${err && err.name}: ${err && err.message}`)
    }
  }

  const inside = path.join(PROJECT_ROOT, 'outputs', 'wenmai-3d', 'probe.txt')
  try {
    suite.eq('inside absolute path resolves unchanged', call(inside), inside)
    suite.eq(
      'relative path resolves against projectRoot',
      call('outputs/wenmai-3d/probe.txt'),
      path.join(PROJECT_ROOT, 'outputs', 'wenmai-3d', 'probe.txt'),
    )
  } catch (err) {
    suite.fail('inside paths are accepted', String(err && err.message))
  }
  expectThrow('path outside the project root is rejected', 'C:\\Windows\\Temp\\wm.txt')
  expectThrow('parent traversal is rejected', path.join(PROJECT_ROOT, 'outputs', '..', '..', 'evil.txt'))
  expectThrow('relative traversal is rejected', '..\\..\\evil.txt')
  expectThrow('sibling-prefix directory is rejected', PROJECT_ROOT + '-evil\\probe.txt')
  expectThrow('drive root is rejected', 'C:\\')
  expectThrow('empty path is rejected', '')

  if (requireProjectFile) {
    const existing = path.join(PROJECT_ROOT, 'AGENTS.md')
    if (statFile(existing).exists) {
      try {
        suite.eq('requireProjectFile accepts an existing project file', requireProjectFile.fn(cfg, 'AGENTS.md'), existing)
      } catch (err) {
        suite.fail('requireProjectFile accepts an existing project file', String(err && err.message))
      }
    } else {
      suite.skip('requireProjectFile accepts an existing project file', 'AGENTS.md not found')
    }
    try {
      requireProjectFile.fn(cfg, 'outputs\\wenmai-3d\\does-not-exist.txt')
      suite.fail('requireProjectFile rejects a missing file', 'no throw')
    } catch (err) {
      suite.ok('requireProjectFile rejects a missing file', err.name === 'PathViolation', String(err && err.message))
    }
  } else {
    suite.notReady('requireProjectFile', 'not exported')
  }

  if (resolveOutputDir) {
    const fallback = path.join(PROJECT_ROOT, 'outputs', 'wenmai-3d', 'reports')
    try {
      suite.eq('resolveOutputDir uses the fallback for undefined', resolveOutputDir.fn(cfg, undefined, fallback), fallback)
      suite.eq(
        'resolveOutputDir resolves an explicit dir',
        resolveOutputDir.fn(cfg, 'outputs/wenmai-3d/qa', fallback),
        path.join(PROJECT_ROOT, 'outputs', 'wenmai-3d', 'qa'),
      )
      try {
        resolveOutputDir.fn(cfg, 'C:\\Temp', fallback)
        suite.fail('resolveOutputDir rejects an outside dir', 'no throw')
      } catch {
        suite.ok('resolveOutputDir rejects an outside dir', true)
      }
    } catch (err) {
      suite.fail('resolveOutputDir is callable', String(err && err.message))
    }
  }
}

// --------------------------------------------------------------- 4. job id

section('job id format (CONTRACT §2: 20261022-001234-generate_roof-ab12)')
const JOB_ID_RE = /^(\d{8})-(\d{6})-([A-Za-z0-9_]+)-([a-z0-9]{2,12})$/
const makeJobId = pick(['makeJobId', 'newJobId', 'jobId'])

if (!loaded.ok) {
  suite.notReady('makeJobId', loaded.reason)
} else if (!makeJobId) {
  suite.notReady('makeJobId', 'no exported makeJobId found')
} else {
  try {
    const id = makeJobId.fn('generate_roof')
    const match = typeof id === 'string' ? id.match(JOB_ID_RE) : null
    suite.ok('makeJobId matches the contract format', !!match, `got ${JSON.stringify(id)}`)
    if (match) {
      const when = new Date(
        Number(match[1].slice(0, 4)),
        Number(match[1].slice(4, 6)) - 1,
        Number(match[1].slice(6, 8)),
        Number(match[2].slice(0, 2)),
        Number(match[2].slice(2, 4)),
        Number(match[2].slice(4, 6)),
      )
      suite.ok('makeJobId timestamp is recent', Math.abs(Date.now() - when.getTime()) < 6 * 3600 * 1000, `${match[1]}-${match[2]}`)
      suite.eq('makeJobId embeds the task name', match[3], 'generate_roof')
    }
    const ids = new Set()
    let dupes = 0
    for (let i = 0; i < 200; i += 1) {
      const one = makeJobId.fn('generate_roof')
      if (ids.has(one)) dupes += 1
      ids.add(one)
    }
    suite.ok('makeJobId is unique across 200 calls', dupes === 0, `${dupes} duplicate(s)`)
    suite.ok(
      'makeJobId is filesystem-safe',
      !/[<>:"/\\|?*\s]/.test(makeJobId.fn('generate_roof')),
      'job id contains a character Windows rejects in a directory name',
    )
  } catch (err) {
    suite.fail('makeJobId is callable', String(err && err.stack))
  }
}

// ------------------------------------------------- 5. result normalisation

section('result normalisation (CONTRACT §2 result shape)')
const makeLocalResult = pick(['makeLocalResult', 'normaliseResult', 'normalizeResult'])
const asTaskResult = pick(['asTaskResult'])

if (!loaded.ok) {
  suite.notReady('makeLocalResult', loaded.reason)
} else if (!makeLocalResult) {
  suite.notReady('makeLocalResult', 'no exported makeLocalResult/normaliseResult found')
} else {
  try {
    const probe = path.join(PROJECT_ROOT, 'outputs', 'wenmai-3d', 'tests', 'probe-artifact.txt')
    fs.mkdirSync(path.dirname(probe), { recursive: true })
    fs.writeFileSync(probe, 'probe\n', 'utf8')

    const shaped = makeLocalResult.fn({
      task: 'build_scene_spec',
      projectRoot: PROJECT_ROOT,
      artifacts: [{ kind: 'json', path: probe }, { kind: 'json', path: path.join(PROJECT_ROOT, 'outputs', 'wenmai-3d', 'tests', 'nope.json') }],
      checks: [{ id: 'probe', status: 'pass', detail: 'ok' }],
      warnings: ['w'],
      notes: 'n',
      metrics: { anchors: 15 },
    })
    suite.eq('makeLocalResult sets ok=true', shaped.ok, true)
    suite.eq('makeLocalResult keeps task', shaped.task, 'build_scene_spec')
    suite.ok('makeLocalResult provides a jobId', typeof shaped.jobId === 'string' && shaped.jobId.length > 0, String(shaped.jobId))
    suite.ok('makeLocalResult keeps checks', Array.isArray(shaped.checks) && shaped.checks.length === 1, JSON.stringify(shaped.checks))
    suite.ok('makeLocalResult keeps warnings', Array.isArray(shaped.warnings) && shaped.warnings.length === 1, JSON.stringify(shaped.warnings))
    suite.ok('makeLocalResult keeps extra fields', shaped.metrics && shaped.metrics.anchors === 15, JSON.stringify(shaped.metrics))
    suite.ok('makeLocalResult normalises artifacts to an array', Array.isArray(shaped.artifacts) && shaped.artifacts.length === 2)

    if (Array.isArray(shaped.artifacts) && shaped.artifacts.length === 2) {
      const [live, dead] = shaped.artifacts
      suite.ok('artifact bytes are measured on disk', live.bytes > 0, `bytes=${live.bytes}`)
      suite.ok('artifact existence is measured on disk', live.exists === true, `exists=${live.exists}`)
      suite.ok('missing artifact reports exists=false and bytes=0', dead.exists === false && dead.bytes === 0, JSON.stringify(dead))
      suite.ok(
        'artifact gets a project-relative path with forward slashes',
        typeof live.relativePath === 'string' && live.relativePath.startsWith('outputs/wenmai-3d/tests/'),
        String(live.relativePath),
      )
    }
    suite.ok(
      'makeLocalResult output satisfies a registry-style output schema',
      checkValueAgainstSchema(
        shaped,
        {
          type: 'object',
          required: ['ok', 'task', 'artifacts'],
          properties: {
            ok: { type: 'boolean' },
            task: { type: 'string' },
            artifacts: { type: 'array', items: { type: 'object' } },
          },
        },
        'makeLocalResult',
      ).length === 0,
    )
  } catch (err) {
    suite.fail('makeLocalResult is callable', String(err && err.stack))
  }
}

if (!loaded.ok) {
  suite.notReady('asTaskResult', loaded.reason)
} else if (!asTaskResult) {
  suite.notReady('asTaskResult', 'not exported')
} else {
  // `asTaskResult` is a compile-time cast in this package (`value as TaskResult`),
  // so the only runtime contract it has is identity. Runtime shaping is
  // `makeLocalResult`'s job and is asserted above.
  try {
    const input = { ok: true, task: 't', artifacts: [{ kind: 'x', path: 'p', bytes: 1 }] }
    const a = asTaskResult.fn(input)
    suite.ok('asTaskResult is an identity cast at runtime', a === input, `same reference: ${a === input}`)
    suite.ok('asTaskResult preserves artifacts', Array.isArray(a.artifacts) && a.artifacts.length === 1, JSON.stringify(a.artifacts))
    const b = asTaskResult.fn({ task: 't' })
    suite.ok('asTaskResult does not invent fields', b.ok === undefined, JSON.stringify(b))
  } catch (err) {
    suite.fail('asTaskResult is callable', String(err && err.stack))
  }
}

// -------------------------------------------------------- 6. schema compile

section('registry schema compiler (compileParams)')
const compileParams = pick(['compileParams'])
if (!loaded.ok) {
  suite.notReady('compileParams', loaded.reason)
} else if (!compileParams) {
  suite.notReady('compileParams', 'not exported')
} else {
  try {
    const schema = compileParams.fn({
      blend: { type: 'string', required: true, description: 'path to .blend' },
      style: { type: 'string', enum: ['hip', 'gable'], default: 'hip' },
      views: { type: 'array', items: { type: 'string' } },
      budget: { type: 'object', properties: { mb: { type: 'number' }, triangles: { type: 'integer', required: true } } },
    })
    suite.ok('compileParams output passes the registry schema check', validateToolSchema(schema, 'compileParams').length === 0, JSON.stringify(validateToolSchema(schema, 'compileParams')))
    suite.eq('compileParams root type', schema.type, 'object')
    suite.eq('compileParams collects required', JSON.stringify(schema.required), JSON.stringify(['blend']))
    suite.eq('compileParams closes the object', schema.additionalProperties, false)
    suite.eq('compileParams keeps the enum', JSON.stringify(schema.properties.style.enum), JSON.stringify(['hip', 'gable']))
    suite.eq('compileParams keeps the default', schema.properties.style.default, 'hip')
    suite.eq('compileParams compiles array items', schema.properties.views.items.type, 'string')
    suite.eq('compileParams compiles nested object required', JSON.stringify(schema.properties.budget.required), JSON.stringify(['triangles']))
    suite.ok('compileParams keeps descriptions', typeof schema.properties.blend.description === 'string' && schema.properties.blend.description.length > 0)

    const noRequired = compileParams.fn({ a: { type: 'string' } })
    suite.ok('compileParams omits required when nothing is required', noRequired.required === undefined, JSON.stringify(noRequired.required))
  } catch (err) {
    suite.fail('compileParams is callable', String(err && err.stack))
  }
}

// ----------------------------------------------------- 7. presentation layer

section('presentation (renderValue / describeParams)')
const renderValue = pick(['renderValue'])
const describeParams = pick(['describeParams'])
if (!loaded.ok) {
  suite.notReady('renderValue', loaded.reason)
} else if (!renderValue) {
  suite.notReady('renderValue', 'not exported')
} else {
  try {
    const blocks = renderValue.fn('wm_export_glb', {
      ok: true,
      artifacts: [{ kind: 'glb', path: 'D:\\x.glb', relativePath: 'outputs/x.glb', bytes: 10 }],
      metrics: { triangles: 5 },
      checks: [
        { id: 'a', status: 'pass', detail: 'ok' },
        { id: 'b', status: 'warn', detail: 'thin' },
      ],
      warnings: ['w1'],
      notes: 'hello',
    })
    suite.ok('renderValue returns at least one block', Array.isArray(blocks) && blocks.length >= 1, JSON.stringify(blocks))
    suite.ok(
      'renderValue blocks are text content',
      Array.isArray(blocks) && blocks.every((b) => b.type === 'text' && typeof b.text === 'string'),
      JSON.stringify(blocks),
    )
    const text = Array.isArray(blocks) && blocks[0] ? blocks[0].text : ''
    suite.ok('renderValue reports ok status', /STATUS:\s*ok/i.test(text), text.slice(0, 200))
    suite.ok('renderValue lists artifacts', /ARTIFACTS:/i.test(text) && /outputs\/x\.glb/.test(text), text.slice(0, 400))
    suite.ok('renderValue summarises checks', /CHECKS:/i.test(text), text.slice(0, 400))
    suite.ok('renderValue surfaces warnings', /WARNINGS:/i.test(text), text.slice(0, 400))
    suite.ok('renderValue is bounded', text.length < 20000, `length=${text.length}`)

    const failed = renderValue.fn('wm_x', { ok: false, error: { message: 'boom' } })
    const failedText = failed && failed[0] ? failed[0].text : ''
    suite.ok('renderValue reports failure status', /STATUS:\s*failed/i.test(failedText) && /boom/.test(failedText), failedText.slice(0, 200))
  } catch (err) {
    suite.fail('renderValue is callable', String(err && err.stack))
  }
}

if (describeParams) {
  try {
    const text = describeParams.fn({ blend: { type: 'string', required: true }, style: { type: 'string', enum: ['hip'] } })
    suite.ok('describeParams marks required params', /blend/.test(text) && /required/i.test(text), String(text).slice(0, 200))
    suite.ok('describeParams marks optional params', /style/.test(text) && /optional/i.test(text), String(text).slice(0, 200))
  } catch (err) {
    suite.fail('describeParams is callable', String(err && err.message))
  }
} else {
  suite.notReady('describeParams', 'not exported')
}

// ------------------------------------------------------- 8. contract sanity

section('contract table sanity')
suite.eq('contract lists 17 tools', CONTRACT_TOOL_NAMES.length, 17)
suite.eq('contract tool names are unique', new Set(CONTRACT_TOOL_NAMES).size, 17)
for (const t of CONTRACT_TOOL_NAMES) {
  const meta = contractTool(t)
  const dupes = meta.params.filter((p, i) => meta.params.indexOf(p) !== i)
  suite.ok(`contract params for ${t} are unique`, dupes.length === 0, JSON.stringify(dupes))
}
suite.ok(
  'every §4 "required" param is also in the param list',
  CONTRACT_TOOL_NAMES.every((t) => contractTool(t).required.every((r) => contractTool(t).params.includes(r))),
  'internal harness table inconsistency',
)

// ------------------------------------------- 9. validator self-test

section('harness schema validator self-test (so a pass cannot be vacuous)')
const goodSchema = { type: 'object', properties: { blend: { type: 'string' } }, required: ['blend'], additionalProperties: false }
const badSchemas = [
  { rootNotObject: true },
  { type: 'object', properties: {}, required: ['ghost'] },
  { type: 'object', properties: { a: { type: 'array' } } },
  { type: 'object', properties: { a: { description: 'no type at all' } } },
]
suite.eq('validator accepts a valid object schema', validateToolSchema(goodSchema).length, 0)
badSchemas.forEach((bad, i) => {
  suite.ok(`validator rejects invalid schema #${i + 1}`, validateToolSchema(bad).length > 0, JSON.stringify(bad))
})

// ------------------------------------------------------------------ finish

const summary = suite.summary()
evidence.checks = summary.entries
evidence.counts = { pass: summary.pass, fail: summary.fail, skip: summary.skip, not_ready: summary.not_ready }
evidence.durationMs = summary.durationMs
evidence.finishedAt = stamp()
evidence.exitCode = summary.exitCode

try {
  const file = path.join(ARTIFACT_ROOT, `unit-${fileStamp()}.json`)
  writeJson(file, evidence)
  writeJson(path.join(ARTIFACT_ROOT, 'unit-last.json'), evidence)
  console.log(`# evidence: ${file}`)
} catch (err) {
  console.log(`# could not write unit evidence: ${err.message}`)
}

if (args.strict && summary.not_ready > 0 && summary.fail === 0) {
  console.log('# --strict: NOT READY counts as failure')
  process.exit(1)
}
process.exit(summary.exitCode)
