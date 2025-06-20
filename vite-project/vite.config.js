import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    allowedHosts: ["delicate-generally-gelding.ngrok-free.app"],
    proxy: {
      '/api': {
        target: "http://localhost:8000",
        secure: false,
        changeOrigin: true,
      },
      '/react/static': {
        target: 'http://127.0.0.1:8000',
        secure: false,
        changeOrigin: true,
        // Ensure the path is not rewritten, so backend sees /react/static/...
        // If you ever need to rewrite, use the line below:
        // rewrite: (path) => path.replace(/^\/react\/static/, '/react/static'),
      }
    },
  },
  base: "/react/"
})