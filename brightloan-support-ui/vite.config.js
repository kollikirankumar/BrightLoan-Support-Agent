import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Proxies /auth and /chat to the FastAPI backend during local dev
// so the browser never has to deal with cross-origin cookies.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/auth': 'http://localhost:8000',
      '/chat': 'http://localhost:8000',
    },
  },
})
