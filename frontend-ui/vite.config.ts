import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";


import tailwindcss from "@tailwindcss/vite"; // 引入新插件

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(), // 添加到插件列表
  ],
  // 关键：确保端口与 Tauri 配置一致
  server: {
    port: 1420,
    strictPort: true,
    host: true,
  },
});