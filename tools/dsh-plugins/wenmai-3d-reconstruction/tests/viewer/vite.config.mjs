import { defineConfig } from 'vite'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const here = path.dirname(fileURLToPath(import.meta.url))
const threeRoot = 'D:/wenmai-huazhang/frontend/node_modules/three'

// The viewer intentionally runs on the frontend's own three.js version, so the
// browser check exercises the exact renderer the gallery uses — without touching
// the gallery app (which another workstream edits concurrently).
export default defineConfig({
  root: here,
  publicDir: path.join(here, 'public'),
  resolve: {
    alias: [
      { find: /^three\/addons\//, replacement: `${threeRoot}/examples/jsm/` },
      { find: /^three$/, replacement: `${threeRoot}/build/three.module.js` },
    ],
  },
  server: {
    port: 5199,
    strictPort: true,
    fs: { allow: ['D:/wenmai-huazhang'] },
  },
})
