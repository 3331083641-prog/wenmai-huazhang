/**
 * Dependency-free static server for the plugin's GLB verification page.
 *
 * Vite was tried first, but this harness runs `vite` through
 * `ELECTRON_RUN_AS_NODE`, which exits before binding. A ~90-line node:http
 * server is deterministic and needs no install:
 *
 *   /                -> tests/viewer/index.html
 *   /main.js         -> tests/viewer/main.js
 *   /models/*        -> tests/viewer/public/models/*
 *   /vendor/three/*  -> frontend/node_modules/three/*  (SAME three as the app)
 *
 * The page uses an import map (see index.html) so `three` and `three/addons/*`
 * resolve to the frontend's own copy.
 */
import { createReadStream, existsSync, statSync } from 'node:fs'
import http from 'node:http'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const projectRoot = path.resolve(here, '..', '..', '..', '..', '..')
const threeRoot = path.join(projectRoot, 'frontend', 'node_modules', 'three')
const port = Number(process.env.WM_VIEWER_PORT || 5199)

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.glb': 'model/gltf-binary',
  '.gltf': 'model/gltf+json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.ktx2': 'image/ktx2',
  '.bin': 'application/octet-stream',
}

function send(res, status, body, type = 'text/plain; charset=utf-8') {
  res.writeHead(status, { 'Content-Type': type, 'Cache-Control': 'no-store' })
  res.end(body)
}

function serveFile(res, filePath) {
  if (!existsSync(filePath) || !statSync(filePath).isFile()) {
    send(res, 404, `not found: ${filePath}`)
    return
  }
  const type = MIME[path.extname(filePath).toLowerCase()] || 'application/octet-stream'
  res.writeHead(200, {
    'Content-Type': type,
    'Content-Length': statSync(filePath).size,
    'Cache-Control': 'no-store',
  })
  createReadStream(filePath).pipe(res)
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://127.0.0.1:${port}`)
  let pathname = decodeURIComponent(url.pathname)

  if (pathname === '/' || pathname === '/index.html') {
    serveFile(res, path.join(here, 'index.html'))
    return
  }
  if (pathname === '/main.js') {
    serveFile(res, path.join(here, 'main.js'))
    return
  }
  if (pathname.startsWith('/models/')) {
    serveFile(res, path.join(here, 'public', 'models', pathname.slice('/models/'.length)))
    return
  }
  if (pathname.startsWith('/vendor/three/')) {
    const rest = pathname.slice('/vendor/three/'.length)
    const target = path.join(threeRoot, rest)
    if (!target.startsWith(threeRoot)) {
      send(res, 403, 'forbidden')
      return
    }
    serveFile(res, target)
    return
  }
  send(res, 404, `no route for ${pathname}`)
})

server.listen(port, '127.0.0.1', () => {
  console.log(`[wm-viewer] http://127.0.0.1:${port}/  three=${threeRoot}`)
})
