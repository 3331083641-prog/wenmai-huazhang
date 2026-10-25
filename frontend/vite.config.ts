import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {defineConfig} from 'vite';

export default defineConfig(() => {
  return {
    base: process.env.VITE_PUBLIC_BASE || '/',
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      // Do not modifyâfile watching is disabled to prevent flickering during agent edits.
      hmr: process.env.DISABLE_HMR !== 'true',
      // Runtime cases use /cases; asset writes must not reset an open interaction.
      watch: { ignored: (file: string) => /\/(?:docs\/examples|public\/interactive)\/[^/]+-20\d{6}-[^/]+(?:\/|$)/
        .test(file.replace(/\\/g, '/')) },
    },
  };
});
