import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteSingleFile } from 'vite-plugin-singlefile'

// The build writes a single self-contained index.html into the Python package. The Python
// side replaces __CODEWALK_DATA__ and __CODEWALK_TITLE__ in it (see codewalk/build.py).
export default defineConfig({
  plugins: [react(), viteSingleFile()],
  build: {
    outDir: '../src/codewalk/viewer',
    emptyOutDir: true,
    target: 'es2020',
    cssCodeSplit: false,
    assetsInlineLimit: 100_000_000,
    chunkSizeWarningLimit: 20_000,
    reportCompressedSize: false,
  },
})
