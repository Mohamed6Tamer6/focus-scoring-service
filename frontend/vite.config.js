import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    server: {
        port: 3000,
        proxy: {
            '/api/focus/ws': {
                target: 'wss://vivacious-nurturing-production.up.railway.app',
                ws: true,
                secure: true,
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api/, '')
            },
            '/api': {
                target: 'https://vivacious-nurturing-production.up.railway.app',
                changeOrigin: true,
                secure: true,
                rewrite: (path) => path.replace(/^\/api/, '')
            }
        }
    }
})
