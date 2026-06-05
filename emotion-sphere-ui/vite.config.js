import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  envPrefix: ['VITE_', 'NEXT_PUBLIC_'],
  plugins: [react()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  publicDir: 'public',
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'three': ['three', '@react-three/fiber', '@react-three/drei'],
          'pdf': ['jspdf', 'html2canvas'],
        },
      },
    },
  },
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/wdbible': {
        target: 'https://wd.bible',
        changeOrigin: true,
        rewrite: path => path.replace(/^\/wdbible/, ''),
      },
    },
  },
  preview: {
    port: 4173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/wdbible': {
        target: 'https://wd.bible',
        changeOrigin: true,
        rewrite: path => path.replace(/^\/wdbible/, ''),
      },
    },
  },
})
