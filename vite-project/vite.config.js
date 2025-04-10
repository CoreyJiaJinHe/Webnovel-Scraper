import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(),tailwindcss()],
  server: {
    allowedHosts:["delicate-generally-gelding.ngrok-free.app"],
    proxy: {
      '/api': {
        target: "http://localhost:8080",
        secure: false,
        changeOrigin: true,
        //rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  base:"/react/"
})
