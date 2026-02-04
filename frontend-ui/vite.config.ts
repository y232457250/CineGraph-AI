import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import { fileURLToPath } from 'url';

import tailwindcss from "@tailwindcss/vite"; // 引入新插件

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(), // 添加到插件列表
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src")
    }
  },
  // 关键：确保端口与 Tauri 配置一致
  server: {
    port: 1420,
    strictPort: true,
    host: true,
  }
});