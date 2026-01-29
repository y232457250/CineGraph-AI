// check-env.js
import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';

console.log("🚀 开始检测 CineGraph-AI 开发环境 (ESM Mode)...\n");

function check(name, command) {
    try {
        const output = execSync(command, { stdio: 'pipe' }).toString().split('\n')[0].trim();
        console.log(`✅ ${name}: ${output}`);
        return true;
    } catch (e) {
        console.log(`❌ ${name} 未安装或未找到 (执行: ${command})`);
        return false;
    }
}

const results = [
    check("Node.js", "node -v"),
    check("Rustc", "rustc --version"),
    check("Cargo", "cargo --version"),
    check("NPM", "npm -v"),
    check("Tauri CLI", "npx tauri -V"),
];

// 检测 D 盘目录结构
const baseDataPath = "D:\\AI\\CineGraph-AI\\data";
const folders = ['media', 'subtitles', 'chroma_db', 'annotations'];

console.log("\n文件夹结构检测:");
folders.forEach(folder => {
    const fullPath = path.join(baseDataPath, folder);
    if (fs.existsSync(fullPath)) {
        console.log(`✅ 目录已就绪: ${fullPath}`);
    } else {
        console.log(`⚠️ 目录缺失: ${fullPath} (请手动创建以存储数据)`);
    }
});

if (results.every(r => r)) {
    console.log("\n✨ 环境基础搭建成功！");
    console.log("👉 下一步：运行 'npm run tauri dev' 启动 Tauri 窗口。");
} else {
    console.log("\n❌ 请根据报错信息检查环境配置。如果是初次安装 Rust，请重启 VS Code 或终端。");
}