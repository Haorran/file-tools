import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import tailwindcss from '@tailwindcss/vite';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const manifestPath = path.resolve(__dirname, '../manifest');
let appVersion = '1.0.0';
try {
  const manifest = fs.readFileSync(manifestPath, 'utf-8');
  const match = manifest.match(/^version\s*=\s*(\S+)/m);
  if (match) appVersion = match[1];
} catch {}

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  base: '/app/file-tools/',
  define: {
    __APP_VERSION__: JSON.stringify(appVersion),
  },
  build: {
    outDir: '../app/server/www',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/app/file-tools/api': { target: 'http://localhost:3001', changeOrigin: true },
    },
  },
});
