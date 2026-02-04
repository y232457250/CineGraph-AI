import ReactDOM from "react-dom/client";
import { StrictMode } from 'react';
import App from "./App";
import "./index.css"; // 确保 index.css 引入了 tailwind

// 显示 Tauri 窗口
const showTauriWindow = async () => {
  try {
    const { getCurrentWindow } = await import('@tauri-apps/api/window');
    const win = getCurrentWindow();
    await win.show();
    await win.setFocus();
    console.log('✅ Tauri 窗口已显示');
  } catch (e) {
    // 不在 Tauri 环境中（比如浏览器开发），忽略
    console.log('ℹ️ 非 Tauri 环境，跳过窗口显示');
  }
};

// 隐藏启动画面并显示窗口
const hideSplashScreen = async () => {
  // 先显示 Tauri 窗口
  await showTauriWindow();
  
  // 然后隐藏启动画面
  const splash = document.getElementById('splash-screen');
  if (splash) {
    // 添加渐隐动画
    splash.classList.add('fade-out');
    // 动画结束后移除元素
    setTimeout(() => {
      splash.remove();
    }, 500);
  }
};

// 渲染应用
ReactDOM.createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App onReady={hideSplashScreen} />
  </StrictMode>,
);