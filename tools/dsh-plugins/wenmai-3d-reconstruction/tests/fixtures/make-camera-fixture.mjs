#!/usr/bin/env node
/**
 * Generate `camera-correspondences.json` — a *synthetic but internally exact*
 * 3D↔pixel fixture for `wm_match_camera`.
 *
 * Why synthetic: the ten concept images are stylised illustrations, so there is
 * no trustworthy pixel measurement of a real camera in them. Inventing "the
 * measured pixel" would be fabricated evidence. Instead this fixture states an
 * explicit pinhole camera as ground truth, projects known building landmarks
 * through it, and stores the pairs. The solver therefore has a **known correct
 * answer**: a correct solve must drive the reprojection RMS to ~0 px, and a
 * broken solve cannot fake it. Nothing here is extracted from a reference photo.
 *
 *   node tests/fixtures/make-camera-fixture.mjs
 *
 * Convention (matches CONTRACT §1 and reference.ts): Z up, +X right, front −Y,
 * pixels origin top-left, u → right, v → down, principal point at the centre.
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = path.dirname(fileURLToPath(import.meta.url))

const WIDTH = 1448
const HEIGHT = 1086
const SENSOR_MM = 36
const LENS_MM = 35

const CAMERA = {
  position: [-22.425, -24.725, 10.971],
  target: [0, 0.55, 5.7],
  lensMm: LENS_MM,
  sensorWidthMm: SENSOR_MM,
  rollDeg: 0,
}

const vsub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]]
const vadd = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]]
const vscale = (a, s) => [a[0] * s, a[1] * s, a[2] * s]
const vdot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
const vcross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
const vnorm = (a) => Math.sqrt(vdot(a, a))
const normalize = (a) => {
  const n = vnorm(a)
  return n === 0 ? [0, 0, 0] : vscale(a, 1 / n)
}

/** Right-handed camera basis: right, up, forward(-Z view). */
function basis(cam) {
  const forward = normalize(vsub(cam.target, cam.position))
  const worldUp = [0, 0, 1]
  let right = normalize(vcross(forward, worldUp))
  let up = vcross(right, forward)
  if (cam.rollDeg) {
    const r = (cam.rollDeg * Math.PI) / 180
    const r2 = vadd(vscale(right, Math.cos(r)), vscale(up, Math.sin(r)))
    const u2 = vadd(vscale(up, Math.cos(r)), vscale(right, -Math.sin(r)))
    right = normalize(r2)
    up = normalize(u2)
  }
  return { forward, right, up }
}

function project(cam, point) {
  const { forward, right, up } = basis(cam)
  const d = vsub(point, cam.position)
  const depth = vdot(d, forward)
  if (depth <= 1e-6) return null
  const x = vdot(d, right)
  const y = vdot(d, up)
  const fPx = (cam.lensMm / cam.sensorWidthMm) * WIDTH
  const u = WIDTH / 2 + (fPx * x) / depth
  const v = HEIGHT / 2 - (fPx * y) / depth
  return { u: round(u), v: round(v), depth: round(depth) }
}

const round = (n) => Math.round(n * 1000) / 1000

// Building landmarks from CONTRACT §1 (metres).
const LANDMARKS = [
  { label: 'plinth front-left top', point3d: [-8, -8, 0] },
  { label: 'plinth front-right top', point3d: [8, -8, 0] },
  { label: 'plinth back-right top', point3d: [8, 8, 0] },
  { label: 'plinth back-left top', point3d: [-8, 8, 0] },
  { label: 'stair foot centre', point3d: [0, -8, 0] },
  { label: 'wall corner front-left @floor1', point3d: [-4.2, -3.2, 0.25] },
  { label: 'wall corner front-right @floor1', point3d: [4.2, -3.2, 0.25] },
  { label: 'wall corner back-left @floor1', point3d: [-4.2, 4.3, 0.25] },
  { label: 'wall corner back-right @floor1', point3d: [4.2, 4.3, 0.25] },
  { label: 'wall corner front-left @wall head', point3d: [-4.2, -3.2, 6.55] },
  { label: 'wall corner front-right @wall head', point3d: [4.2, -3.2, 6.55] },
  { label: 'eave centre', point3d: [0, 0.55, 6.15] },
  { label: 'ridge left', point3d: [-1.35, 0.55, 11.3] },
  { label: 'ridge right', point3d: [1.35, 0.55, 11.3] },
]

const correspondences = []
for (const landmark of LANDMARKS) {
  const p = project(CAMERA, landmark.point3d)
  if (!p) throw new Error(`landmark behind the camera: ${landmark.label}`)
  if (p.u < 0 || p.u > WIDTH || p.v < 0 || p.v > HEIGHT) {
    throw new Error(`landmark projects outside the frame: ${landmark.label} → ${p.u},${p.v}`)
  }
  correspondences.push({
    label: landmark.label,
    point3d: landmark.point3d,
    pixel: [p.u, p.v],
  })
}

const fixture = {
  schemaVersion: 1,
  synthetic: true,
  purpose:
    'Ground-truth pinhole camera for wm_match_camera. The camera below is stated by construction, not measured from a photograph; ' +
    'the pixel coordinates are its exact projections. A correct solve must reach ~0 px reprojection RMS.',
  image: 'assets/gallery3d/references/raw/attachment-11f23a89c6a08bd413c5aa743712f581.png',
  imageSize: [WIDTH, HEIGHT],
  groundTruthCamera: {
    ...CAMERA,
    sensorFit: 'HORIZONTAL',
    fovDegHorizontal: round((2 * Math.atan(SENSOR_MM / 2 / LENS_MM) * 180) / Math.PI),
    note: 'pixel origin top-left, u right, v down; principal point at image centre',
  },
  expectedRmsPx: 0,
  toleranceRmsPx: 2.0,
  correspondences,
}

const outFile = path.join(HERE, 'camera-correspondences.json')
fs.writeFileSync(outFile, JSON.stringify(fixture, null, 2) + '\n', 'utf8')
console.log(`wrote ${outFile} (${correspondences.length} correspondences)`)
for (const c of correspondences) console.log(`  ${c.label}: [${c.point3d.join(', ')}] → (${c.pixel.join(', ')})`)
