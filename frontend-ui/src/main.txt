from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
import re
from pathlib import Path

# --- 1. 定义数据模型 ---
class ScanRequest(BaseModel):
    path: str

# --- 2. 扫描器逻辑 (直接整合在这里方便调试) ---
class MediaScanner:
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        # 匹配开头是数字（豆瓣ID），后面是名字的文件夹
        self.folder_pattern = re.compile(r'^(\d+)(.+)$')
        self.video_exts = {'.mp4', '.mkv', '.avi', '.mov'}
        self.sub_exts = {'.srt', '.ass', '.vtt'}

    def scan(self):
        results = []
        if not self.base_path.exists():
            return []

        for folder_name in os.listdir(self.base_path):
            folder_path = self.base_path / folder_name
            if not folder_path.is_dir():
                continue

            match = self.folder_pattern.match(folder_name)
            if match:
                douban_id = match.group(1)
                movie_name = match.group(2).strip()
                
                video_file = None
                subtitle_file = None
                
                # 遍历文件夹内的文件
                try:
                    for file in folder_path.iterdir():
                        if file.suffix.lower() in self.video_exts:
                            video_file = str(file)
                        elif file.suffix.lower() in self.sub_exts:
                            subtitle_file = str(file)
                except Exception as e:
                    print(f"读取文件夹 {folder_name} 出错: {e}")
                
                results.append({
                    "douban_id": douban_id,
                    "title": movie_name,
                    "folder": folder_name,
                    "video_path": video_file,
                    "subtitle_path": subtitle_file,
                    "status": "ready" if video_file and subtitle_file else "missing_files"
                })
        return results

# --- 3. 创建 FastAPI 应用 ---
app = FastAPI()

# 配置 CORS，允许 Tauri 前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境下建议设置为具体地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "CineGraph-AI Backend is running"}

@app.post("/api/ingest/scan")
async def scan_directory(request: ScanRequest):
    print(f"收到扫描请求路径: {request.path}")
    if not os.path.exists(request.path):
        raise HTTPException(status_code=400, detail="所选路径不存在")
    
    scanner = MediaScanner(request.path)
    movies = scanner.scan()
    print(f"扫描完成，找到 {len(movies)} 部影片")
    return {"movies": movies}

# --- 4. 启动服务 ---
if __name__ == "__main__":
    # 使用 127.0.0.1 确保本地稳定访问
    uvicorn.run(app, host="127.0.0.1", port=8000)



    