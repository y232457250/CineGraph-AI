@app.get("/video/thumbnail")
async def get_video_thumbnail(path: str, frame: int = 1):
    # 使用FFmpeg生成缩略图 (在后台执行)
    subprocess.run([
        "ffmpeg", "-i", path, "-vf", f"select=eq(n,{frame})", "-vframes", "1", 
        "-f", "image2", "-"
    ], capture_output=True)
    
    # 返回Base64缩略图 (避免文件IO)
    return StreamingResponse(
        thumbnail_data,
        media_type="image/jpeg"
    )