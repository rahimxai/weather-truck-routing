import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Same-origin /api in dev mirrors Vercel, so Django needs no CORS setup.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { '/api': 'http://localhost:8000' },
  },
  // MapLibre and deck.gl are big single modules; they load lazily after first paint.
  build: { chunkSizeWarningLimit: 2000 },
})
