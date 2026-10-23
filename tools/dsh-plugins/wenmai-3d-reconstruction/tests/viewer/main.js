/**
 * Standalone Three.js verification page for plugin-exported GLBs.
 *
 * Why this exists: the project's gallery app is edited by another workstream, so
 * the plugin validates its GLB on an isolated page that still uses the SAME
 * three.js version as the frontend (aliased to `frontend/node_modules/three`).
 *
 * URL params:
 *   model=/models/xxx.glb   GLB to load (served from this viewer's public dir)
 *   view=front34|front|left|right|back|top|eave|floor2|floor1
 *   stats=1                 draw the HUD (default 1)
 */
import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'

const params = new URLSearchParams(location.search)
const modelUrl = params.get('model') || '/models/wenmai_gallery_wm_probe.glb'
const view = params.get('view') || 'front34'
const showStats = params.get('stats') !== '0'

const statusEl = document.getElementById('status')
const statsEl = document.getElementById('stats')
const errorEl = document.getElementById('error')

const app = document.getElementById('app')
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false })
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
renderer.setSize(window.innerWidth, window.innerHeight)
renderer.shadowMap.enabled = true
renderer.shadowMap.type = THREE.PCFSoftShadowMap
renderer.outputColorSpace = THREE.SRGBColorSpace
renderer.toneMapping = THREE.ACESFilmicToneMapping
renderer.toneMappingExposure = 1.05
app.appendChild(renderer.domElement)

const scene = new THREE.Scene()
scene.background = new THREE.Color(0xbfd8ef)

const camera = new THREE.PerspectiveCamera(38, window.innerWidth / window.innerHeight, 0.1, 500)
const controls = new OrbitControls(camera, renderer.domElement)
controls.enableDamping = true
controls.dampingFactor = 0.08

// Lighting rig approximates the Blender capture rig: warm key + cool fill + sky.
const hemi = new THREE.HemisphereLight(0xdfeeff, 0x8a7a63, 1.05)
scene.add(hemi)
const key = new THREE.DirectionalLight(0xfff1d6, 2.3)
key.position.set(18, 26, 14)
key.castShadow = true
key.shadow.mapSize.set(2048, 2048)
key.shadow.camera.near = 1
key.shadow.camera.far = 120
key.shadow.camera.left = -30
key.shadow.camera.right = 30
key.shadow.camera.top = 30
key.shadow.camera.bottom = -30
scene.add(key)
const fill = new THREE.DirectionalLight(0xcfe2ff, 0.75)
fill.position.set(-20, 12, -16)
scene.add(fill)

const VIEW_PRESETS = {
  front34: { azimuth: 38, elevation: 19, distance: 2.35 },
  front: { azimuth: 0, elevation: 10, distance: 2.5 },
  left: { azimuth: -75, elevation: 12, distance: 2.6 },
  right: { azimuth: 75, elevation: 12, distance: 2.6 },
  back: { azimuth: 180, elevation: 12, distance: 2.6 },
  top: { azimuth: 35, elevation: 62, distance: 2.4 },
  eave: { azimuth: 40, elevation: 26, distance: 1.15, target: { y: 0.72 } },
  floor1: { azimuth: 8, elevation: 6, distance: 0.62, target: { y: 0.18 } },
  floor2: { azimuth: -12, elevation: 4, distance: 0.72, target: { y: 0.46 } },
}

window.__VIEWER__ = { ready: false, error: null, stats: null, modelUrl, view }

const loader = new GLTFLoader()
loader.load(
  modelUrl,
  (gltf) => {
    const root = gltf.scene
    scene.add(root)

    let meshes = 0
    let triangles = 0
    const materials = new Set()
    const names = []
    root.traverse((object) => {
      if (!object.isMesh) return
      meshes += 1
      names.push(object.name)
      const geometry = object.geometry
      const index = geometry.getIndex()
      const position = geometry.getAttribute('position')
      if (index) triangles += index.count / 3
      else if (position) triangles += position.count / 3
      const material = object.material
      if (Array.isArray(material)) material.forEach((m) => materials.add(m.uuid))
      else if (material) materials.add(material.uuid)
      object.castShadow = true
      object.receiveShadow = true
    })

    const box = new THREE.Box3().setFromObject(root)
    const size = box.getSize(new THREE.Vector3())
    const center = box.getCenter(new THREE.Vector3())
    const maxSpan = Math.max(size.x, size.y, size.z)

    const preset = VIEW_PRESETS[view] || VIEW_PRESETS.front34
    const target = center.clone()
    if (preset.target?.y !== undefined) target.y = box.min.y + size.y * preset.target.y
    const distance = maxSpan * preset.distance
    const azimuth = THREE.MathUtils.degToRad(preset.azimuth)
    const elevation = THREE.MathUtils.degToRad(preset.elevation)
    camera.position.set(
      target.x + Math.sin(azimuth) * Math.cos(elevation) * distance,
      target.y + Math.sin(elevation) * distance,
      target.z + Math.cos(azimuth) * Math.cos(elevation) * distance,
    )
    camera.near = Math.max(0.05, distance / 200)
    camera.far = distance * 12
    camera.updateProjectionMatrix()
    controls.target.copy(target)
    controls.update()

    const stats = {
      meshes,
      triangles: Math.round(triangles),
      materials: materials.size,
      size: { x: +size.x.toFixed(2), y: +size.y.toFixed(2), z: +size.z.toFixed(2) },
      center: { x: +center.x.toFixed(2), y: +center.y.toFixed(2), z: +center.z.toFixed(2) },
      frames: names.filter((n) => n.startsWith('FRAME_')).length,
      roofObjects: names.filter((n) => n.startsWith('ROOF_') || n.startsWith('TILE_')).length,
    }
    window.__VIEWER__ = { ready: true, error: null, stats, modelUrl, view, box: { min: box.min.toArray(), max: box.max.toArray() } }

    if (showStats) {
      statusEl.textContent = '加载成功 · 无 Three.js 运行错误'
      statusEl.className = 'ok'
      statsEl.textContent = [
        `model: ${modelUrl}`,
        `view: ${view}`,
        `meshes: ${stats.meshes}   triangles: ${stats.triangles.toLocaleString()}`,
        `materials: ${stats.materials}`,
        `size (m): ${stats.size.x} × ${stats.size.y} × ${stats.size.z}`,
        `frames found: ${stats.frames}   roof objects: ${stats.roofObjects}`,
      ].join('\n')
    }
  },
  (progress) => {
    if (progress.total) {
      const pct = Math.round((progress.loaded / progress.total) * 100)
      if (showStats) statusEl.textContent = `加载中… ${pct}%`
    }
  },
  (error) => {
    const message = error?.message || String(error)
    window.__VIEWER__ = { ready: false, error: message, stats: null, modelUrl, view }
    if (showStats) {
      statusEl.textContent = '加载失败'
      statusEl.className = 'err'
      errorEl.textContent = message
    }
    console.error('[wm-viewer]', error)
  },
)

renderer.setAnimationLoop(() => {
  controls.update()
  renderer.render(scene, camera)
})

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight
  camera.updateProjectionMatrix()
  renderer.setSize(window.innerWidth, window.innerHeight)
})
