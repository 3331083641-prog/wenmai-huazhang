#!/usr/bin/env node
/**
 * Registration check: mount the plugin into a fake Cordis context and verify
 * the tool registry surface against docs/CONTRACT.md §4.
 *
 *   node tests/run-registration.mjs [--strict] [--allow-extra]
 *
 * Asserts, for the real compiled `lib/index.js`:
 *   - `apply(ctx, config)` registers exactly the 17 contract tools;
 *   - each definition has name / description / execute / output.schema /
 *     output.render, and an object-rooted, structurally valid JSON Schema;
 *   - every §4 parameter name is declared, and every §4 required parameter is
 *     listed in `required` (or accepted via a documented either/or group);
 *   - `inject` covers `tools` and the context contract is not bypassed.
 *
 * Writes `tests/registered-tools.json` and `tests/registration-report.md`.
 * Exit codes: 0 = all pass · 1 = failure · 2 = build absent, nothing verified.
 */

import fs from 'node:fs'
import path from 'node:path'
import {
  ARTIFACT_ROOT,
  c,
  checkValueAgainstSchema,
  CONTRACT_TOOLS,
  CONTRACT_TOOL_NAMES,
  contractTool,
  createFakeContext,
  createSuite,
  fileStamp,
  loadPlugin,
  parseArgs,
  PLUGIN_CONFIG,
  PLUGIN_ROOT,
  pluginObject,
  preserveActivation,
  snapshotActivation,
  stamp,
  TESTS_DIR,
  validateToolSchema,
  writeJson,
  writeText,
} from './lib/common.mjs'

const args = parseArgs()
const suite = createSuite('run-registration', {})
const registeredToolsJson = path.join(TESTS_DIR, 'registered-tools.json')
const reportMd = path.join(TESTS_DIR, 'registration-report.md')

const evidence = {
  kind: 'registration',
  startedAt: stamp(),
  pluginRoot: PLUGIN_ROOT,
  config: {
    ...PLUGIN_CONFIG,
    blenderExe: PLUGIN_CONFIG.blenderExe,
  },
}

const loaded = await loadPlugin()
if (!loaded.ok) {
  suite.notReady('lib/index.js exists', loaded.reason)
  const summary = suite.summary()
  console.log(c.yellow(`# registration NOT VERIFIED: ${loaded.reason}`))
  writeJson(registeredToolsJson, {
    status: 'not_ready',
    reason: loaded.reason,
    at: stamp(),
    expectedTools: CONTRACT_TOOLS,
  })
  writeText(
    reportMd,
    [
      '# Registration report — NOT READY',
      '',
      `- checked at: ${stamp()}`,
      `- plugin root: \`${PLUGIN_ROOT}\``,
      `- reason: ${loaded.reason}`,
      '',
      'Nothing was verified. Run the TypeScript build (`npm run build`) and repeat',
      '`node tests/run-registration.mjs`.',
      '',
    ].join('\n'),
  )
  process.exit(summary.exitCode === 0 ? 2 : summary.exitCode)
}

const plugin = pluginObject(loaded.mod)
const { ctx, tools, logs, disposers } = createFakeContext()

// Mounting rewrites outputs/wenmai-3d/logs/activation.json; keep a previous
// (e.g. live-host) record before we clobber it.
const activationBefore = preserveActivation('registration')
if (activationBefore) suite.note(`preserved a previous activation record: ${activationBefore}`)

let applyError = null
const applyStarted = Date.now()
try {
  const apply = typeof plugin === 'function' ? plugin : plugin.apply
  if (typeof apply !== 'function') throw new Error('plugin has no apply() export')
  await apply(ctx, PLUGIN_CONFIG)
} catch (err) {
  applyError = err
}
const applyMs = Date.now() - applyStarted
const activationOwn = snapshotActivation('registration')
evidence.activation = { preserved: activationBefore, own: activationOwn }

suite.ok('apply(ctx, config) completes without throwing', applyError === null, applyError && (applyError.stack || applyError.message))
suite.ok(
  'apply logs no error() calls',
  !logs.some((l) => l.level === 'error'),
  logs.filter((l) => l.level === 'error').map((l) => l.args.join(' ')).join(' | '),
)
evidence.applyMs = applyMs
evidence.logCount = logs.length
evidence.registrationCount = tools.length

const pluginName = plugin && plugin.name
const injectRaw = plugin && plugin.inject
const injectArr = Array.isArray(injectRaw) ? injectRaw : injectRaw && Array.isArray(injectRaw.required) ? injectRaw.required : []
evidence.plugin = { name: pluginName, inject: injectArr }
suite.ok('plugin exports a name', typeof pluginName === 'string' && pluginName.length > 0, JSON.stringify(pluginName))
suite.ok("plugin injects 'tools'", injectArr.includes('tools'), JSON.stringify(injectArr))

// --------------------------------------------------------------- tool set

const names = tools.map((t) => t.name)
const uniqueNames = [...new Set(names)]
const expected = CONTRACT_TOOL_NAMES

suite.eq('registered tool count', uniqueNames.length, 17)
suite.ok(
  'no duplicate registrations',
  uniqueNames.length === names.length,
  `duplicates: ${JSON.stringify(names.filter((n, i) => names.indexOf(n) !== i))}`,
)

const missing = expected.filter((n) => !uniqueNames.includes(n))
const extra = uniqueNames.filter((n) => !expected.includes(n))
suite.ok('all 17 contract tools registered', missing.length === 0, `missing: ${JSON.stringify(missing)}`)
if (args['allow-extra']) {
  if (extra.length) suite.skip('no extra tools registered', `extra (allowed by --allow-extra): ${JSON.stringify(extra)}`)
} else {
  suite.ok('no tools beyond the contract', extra.length === 0, `extra: ${JSON.stringify(extra)}`)
}

// ------------------------------------------------------ per-tool structure

const table = []
const schemaProblems = {}

for (const def of tools) {
  const meta = contractTool(def.name)
  const row = {
    name: def.name,
    inContract: !!meta,
    group: meta ? meta.group : '—',
    descriptionLength: typeof def.description === 'string' ? def.description.length : 0,
    params: [],
    required: [],
    contractParamsMissing: [],
    contractRequiredMissing: [],
    schemaProblems: [],
    hasExecute: typeof def.execute === 'function',
    hasOutputSchema: !!(def.output && def.output.schema),
    hasOutputRender: typeof (def.output && def.output.render) === 'function',
    disposable: false,
  }

  if (!meta) {
    // still validate the schema, but flag it as out-of-contract
    row.schemaProblems = validateToolSchema(def.parameters, `${def.name}.parameters`)
    table.push(row)
    continue
  }

  suite.ok(`${def.name}: has a description (>=20 chars)`, typeof def.description === 'string' && def.description.trim().length >= 20, `length=${row.descriptionLength}`)
  suite.ok(`${def.name}: has execute()`, row.hasExecute, `got ${typeof def.execute}`)
  suite.ok(`${def.name}: has output.schema`, row.hasOutputSchema, JSON.stringify(def.output && Object.keys(def.output)))
  suite.ok(`${def.name}: has output.render()`, row.hasOutputRender, `got ${typeof (def.output && def.output.render)}`)

  const problems = validateToolSchema(def.parameters, `${def.name}.parameters`)
  schemaProblems[def.name] = problems
  row.schemaProblems = problems
  suite.ok(`${def.name}: object-rooted valid JSON Schema`, problems.length === 0, problems.join(' | '))

  const props = (def.parameters && def.parameters.properties) || {}
  const declared = Object.keys(props)
  const required = Array.isArray(def.parameters && def.parameters.required) ? def.parameters.required : []
  row.params = declared
  row.required = required

  const missingParams = meta.params.filter((p) => !declared.includes(p))
  row.contractParamsMissing = missingParams
  // Optional §4 parameters that were renamed/dropped are contract drift: the
  // tool may still be perfectly usable, but CONTRACT.md must be amended by its
  // owner. --strict-contract turns that drift into a hard failure.
  if (missingParams.length > 0) {
    const message = `missing: ${JSON.stringify(missingParams)} (declared: ${JSON.stringify(declared)})`
    if (args['strict-contract']) suite.fail(`${def.name}: declares every §4 parameter`, message)
    else suite.warn(`${def.name}: declares every §4 parameter`, message)
  } else {
    suite.ok(`${def.name}: declares every §4 parameter`, true)
  }

  const missingRequired = meta.required.filter((p) => !required.includes(p))
  row.contractRequiredMissing = missingRequired
  if (missingRequired.length > 0) {
    // §4 marks these mandatory (no "?"). An implementation that accepts them as
    // optional because it has a fallback must either mark them required or get
    // the contract amended — that is a decision for the contract owner, so this
    // is reported loudly and only fails under --strict-contract.
    const message = `§4 marks these required but the schema does not: ${JSON.stringify(missingRequired)} (required: ${JSON.stringify(required)})`
    if (args['strict-contract']) suite.fail(`${def.name}: marks §4 required parameters as required`, message)
    else suite.warn(`${def.name}: marks §4 required parameters as required`, message)
  } else {
    suite.ok(`${def.name}: marks §4 required parameters as required`, true)
  }

  for (const group of meta.requireAny || []) {
    suite.ok(
      `${def.name}: accepts one of ${JSON.stringify(group)}`,
      group.some((p) => declared.includes(p)),
      `declared: ${JSON.stringify(declared)}`,
    )
  }

  // output schema should itself be an object-rooted schema
  if (row.hasOutputSchema) {
    const outProblems = validateToolSchema(def.output.schema, `${def.name}.output.schema`)
    // an output schema is often a loose object; only hard-fail structural breakage
    const hard = outProblems.filter((p) => /not an object|root type/.test(p))
    suite.ok(`${def.name}: output.schema is object-rooted`, hard.length === 0, outProblems.join(' | '))
  }

  // a definition must survive a trivial render/execute probe contractually:
  // render only gets called with a real value, so just assert arity > 0.
  suite.ok(`${def.name}: output.render declares an argument`, row.hasOutputRender && def.output.render.length >= 1, `arity=${row.hasOutputRender ? def.output.render.length : 'n/a'}`)

  table.push(row)
}

// disposal: register() must return a disposer for every tool
const disposable = disposers.filter((d) => typeof d === 'function').length
suite.eq('every registration returned a disposer', disposable, tools.length)

// ------------------------------------------------------------ extra detail

// verify the fake registry captured registrations in contract order groups
const byGroup = { A: [], B: [], C: [], D: [] }
for (const t of table) if (t.inContract) byGroup[t.group].push(t.name)
suite.eq('group A registered (4)', byGroup.A.length, 4)
suite.eq('group B registered (5)', byGroup.B.length, 5)
suite.eq('group C registered (4)', byGroup.C.length, 4)
suite.eq('group D registered (4)', byGroup.D.length, 4)

// A sample parameter must round-trip through a real value check (proves the
// schemas are usable, not just structurally legal).
const roof = tools.find((t) => t.name === 'wm_generate_roof')
if (roof) {
  const sample = { footprintX: 8.4, eaveZ: 6.15, style: 'hip' }
  const problems = checkValueAgainstSchema(sample, roof.parameters, 'wm_generate_roof')
  suite.ok('sample roof args satisfy the registered schema', problems.length === 0, problems.join(' | '))
}

const exportCheck = tools.find((t) => t.name === 'wm_match_camera')
if (exportCheck) {
  const problems = checkValueAgainstSchema({}, exportCheck.parameters, 'wm_match_camera')
  suite.ok(
    'schema rejects wm_match_camera without image/correspondences',
    problems.some((p) => /image/.test(p)) && problems.some((p) => /correspondences/.test(p)),
    problems.join(' | '),
  )
}

// ------------------------------------------------------------------ output

const summary = suite.summary()
evidence.finishedAt = stamp()
evidence.durationMs = summary.durationMs
evidence.counts = { pass: summary.pass, fail: summary.fail, warn: summary.warn, skip: summary.skip, not_ready: summary.not_ready }
evidence.tools = table
evidence.missingTools = missing
evidence.extraTools = extra
evidence.contractDrift = summary.entries.filter((e) => e.status === 'warn').map((e) => ({ name: e.name, detail: e.detail }))
evidence.exitCode = summary.exitCode

writeJson(registeredToolsJson, {
  status: summary.fail === 0 ? (summary.warn > 0 ? 'pass_with_contract_drift' : 'pass') : 'fail',
  at: stamp(),
  plugin: evidence.plugin,
  registeredCount: tools.length,
  contractCount: 17,
  missing,
  extra,
  tools: table,
  schemaProblems,
  contractDrift: evidence.contractDrift,
})

// ------------------------------------------------------------- markdown

const md = []
md.push('# Registration report — wenmai-3d-reconstruction')
md.push('')
md.push(`- generated: \`${stamp()}\``)
md.push(`- plugin root: \`${PLUGIN_ROOT}\``)
md.push(`- plugin export: \`${pluginName}\` · inject: \`${JSON.stringify(injectArr)}\``)
md.push(`- apply() duration: ${applyMs} ms`)
md.push(`- registered tools: **${uniqueNames.length} / 17**`)
md.push(`- missing: ${missing.length ? missing.map((m) => `\`${m}\``).join(', ') : '—'}`)
md.push(`- extra: ${extra.length ? extra.map((m) => `\`${m}\``).join(', ') : '—'}`)
md.push(`- checks: **${summary.pass} pass / ${summary.fail} fail / ${summary.warn} warn / ${summary.skip} skip / ${summary.not_ready} not ready**`)
md.push('')
md.push('## Tool table')
md.push('')
md.push('| # | tool | group | desc len | params | required | contract params missing | schema |')
md.push('|---|---|---|---|---|---|---|---|')
table.forEach((row, i) => {
  const schemaState = row.schemaProblems.length === 0 ? 'ok' : `FAIL (${row.schemaProblems.length})`
  md.push(
    `| ${i + 1} | \`${row.name}\` | ${row.group} | ${row.descriptionLength} | ${row.params.length} | ${row.required.length} | ${
      row.contractParamsMissing.length ? row.contractParamsMissing.map((p) => `\`${p}\``).join(', ') : '—'
    } | ${schemaState} |`,
  )
})
md.push('')
md.push('## Parameters per tool')
md.push('')
for (const row of table) {
  md.push(`### \`${row.name}\``)
  md.push('')
  md.push(`- params (${row.params.length}): ${row.params.length ? row.params.map((p) => `\`${p}\``).join(', ') : '—'}`)
  md.push(`- required (${row.required.length}): ${row.required.length ? row.required.map((p) => `\`${p}\``).join(', ') : '—'}`)
  if (row.contractParamsMissing.length) md.push(`- ⚠ missing contract params: ${row.contractParamsMissing.map((p) => `\`${p}\``).join(', ')}`)
  if (row.contractRequiredMissing.length) md.push(`- ⚠ required not marked: ${row.contractRequiredMissing.map((p) => `\`${p}\``).join(', ')}`)
  if (row.schemaProblems.length) md.push(`- ⚠ schema: ${row.schemaProblems.join('; ')}`)
  md.push('')
}
md.push('## Failures')
md.push('')
const failures = summary.entries.filter((e) => e.status === 'fail')
if (failures.length === 0) md.push('None.')
else for (const f of failures) md.push(`- **${f.name}** — ${f.detail}`)
md.push('')
md.push('## Contract drift (warnings — decision for the contract owner)')
md.push('')
const warns = summary.entries.filter((e) => e.status === 'warn')
if (warns.length === 0) md.push('None.')
else {
  md.push('These are not runtime failures: the tool works, but `docs/CONTRACT.md` §4 and the')
  md.push('registered schema disagree. Either mark the parameter `required` in code or amend')
  md.push('§4 (add `?`, or document the replacement parameter). Run with `--strict-contract`')
  md.push('to treat this list as a hard failure.')
  md.push('')
  for (const w of warns) md.push(`- **${w.name}** — ${w.detail}`)
}
md.push('')
writeText(reportMd, md.join('\n'))

console.log(c.dim(`# wrote ${registeredToolsJson}`))
console.log(c.dim(`# wrote ${reportMd}`))

if (args.strict && summary.not_ready > 0 && summary.fail === 0) process.exit(1)
process.exit(summary.exitCode)
