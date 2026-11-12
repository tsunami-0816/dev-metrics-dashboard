import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// D-18/D-30：开发态前端 5184，API 经代理转发到 8091（避免跨域）；
// 演示态由 FastAPI StaticFiles 托管 dist（同源，相对路径直接命中）。
export default defineConfig({
  plugins: [vue()],
  server: {
    host: "127.0.0.1",
    port: 5184,
    strictPort: true,
    proxy: {
      "/api": { target: "http://127.0.0.1:8091", changeOrigin: false },
      "/health": { target: "http://127.0.0.1:8091", changeOrigin: false },
    },
  },
  build: {
    outDir: "dist",
    chunkSizeWarningLimit: 1200,
  },
});
