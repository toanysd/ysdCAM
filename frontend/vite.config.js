import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    dedupe: ['react', 'react-dom'],
  },
  server: {
    watch: {
      usePolling: false, // Force native events, polling on USB kills performance
      ignored: ['**/node_modules/**', '**/.git/**']
    }
  },
  optimizeDeps: {
    // Ép Vite phải pre-bundle các thư viện nặng 1 lần duy nhất bằng esbuild (code C++/Go). 
    // Nếu không, Node.js sẽ phải đọc hàng ngàn file nhỏ của three.js từ USB mỗi lần reload gây treo máy.
    include: ['three', '@react-three/fiber', '@react-three/drei', 'konva', 'react-konva']
  }
})
