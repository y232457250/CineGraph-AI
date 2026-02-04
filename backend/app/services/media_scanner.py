"""
媒体扫描器 - 扫描目录中的视频和字幕文件
"""
import os
import re
import hashlib
import subprocess
from pathlib import Path
from typing import List, Dict


# ffmpeg 路径配置
FFMPEG_PATH = Path(__file__).resolve().parent.parent.parent / "ffmpeg" / "bin" / "ffmpeg.exe"
if not FFMPEG_PATH.exists():
    FFMPEG_PATH = "ffmpeg"
else:
    FFMPEG_PATH = str(FFMPEG_PATH)


def extract_video_thumbnail(video_path: str, output_path: str) -> bool:
    """使用 ffmpeg 截取视频首帧作为封面"""
    try:
        cmd = [
            FFMPEG_PATH,
            '-i', video_path,
            '-ss', '00:00:01',
            '-vframes', '1',
            '-q:v', '2',
            '-y',
            output_path
        ]
        subprocess.run(cmd, capture_output=True, timeout=30)
        return Path(output_path).exists()
    except Exception as e:
        print(f"截取视频封面失败: {e}")
        return False


class MediaScanner:
    """媒体文件扫描器"""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.folder_pattern = re.compile(r'^(\d+)[-\s]+(.+)$')
        self.video_exts = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.ts'}
        self.sub_exts = {'.srt', '.ass', '.vtt'}
        self.episode_pattern = re.compile(r'[Ee][Pp]?(\d+)|第(\d+)[集话]|[Ss]\d+[Ee](\d+)', re.IGNORECASE)
    
    def extract_episode_number(self, filename: str) -> int:
        """从文件名中提取集数"""
        match = self.episode_pattern.search(filename)
        if match:
            for group in match.groups():
                if group:
                    return int(group)
        return 0
    
    def scan(self) -> List[Dict]:
        """扫描目录并返回媒体列表"""
        results = []
        if not self.base_path.exists():
            return []
        
        for folder_name in os.listdir(self.base_path):
            folder_path = self.base_path / folder_name
            if not folder_path.is_dir():
                continue
            
            # 匹配豆瓣ID格式
            match = self.folder_pattern.match(folder_name)
            if match:
                douban_id = match.group(1)
                movie_name = match.group(2).strip()
                is_custom_folder = False
            else:
                folder_hash = hashlib.md5(folder_name.encode('utf-8')).hexdigest()[:8]
                douban_id = f"custom_{folder_hash}"
                movie_name = folder_name.strip()
                is_custom_folder = True
            
            # 收集视频和字幕文件
            video_files = []
            subtitle_files = []
            
            try:
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        file_path = Path(root) / file
                        if file_path.suffix.lower() in self.video_exts:
                            video_files.append(str(file_path))
                        elif file_path.suffix.lower() in self.sub_exts:
                            subtitle_files.append(str(file_path))
            except Exception as e:
                print(f"读取文件夹 {folder_name} 出错: {e}")
            
            # 判断媒体类型
            total_files = max(len(video_files), len(subtitle_files))
            media_type = "tv" if total_files > 1 else "movie"
            
            # 构建 episodes
            episodes = self._build_episodes(video_files, subtitle_files)
            
            # 跳过空文件夹
            if not video_files and not subtitle_files:
                continue
            
            video_file = video_files[0] if video_files else None
            subtitle_file = subtitle_files[0] if subtitle_files else None
            
            # 非豆瓣ID文件夹尝试截取封面
            local_poster = None
            if is_custom_folder and video_file:
                poster_path = folder_path / "poster.jpg"
                if not poster_path.exists():
                    if extract_video_thumbnail(video_file, str(poster_path)):
                        local_poster = str(poster_path)
                else:
                    local_poster = str(poster_path)
            
            result_item = {
                "douban_id": douban_id,
                "title": movie_name,
                "folder": folder_name,
                "video_path": video_file,
                "subtitle_path": subtitle_file,
                "video_count": len(video_files),
                "subtitle_count": len(subtitle_files),
                "media_type": media_type,
                "episodes": episodes if media_type == "tv" else [],
                "status": "ready" if video_file or subtitle_file else "missing_files",
                "is_custom": is_custom_folder
            }
            
            if local_poster:
                result_item["local_poster"] = local_poster
            
            results.append(result_item)
        
        return results
    
    def _build_episodes(self, video_files: List[str], subtitle_files: List[str]) -> List[Dict]:
        """构建剧集列表"""
        episodes = []
        
        # 创建集数映射
        video_episode_map = {vf: self.extract_episode_number(Path(vf).stem) for vf in video_files}
        subtitle_episode_map = {sf: self.extract_episode_number(Path(sf).stem) for sf in subtitle_files}
        
        used_subtitles = set()
        
        if video_files:
            sorted_videos = sorted(video_files, key=lambda x: (video_episode_map.get(x, 0), Path(x).stem.lower()))
            
            for idx, video_path in enumerate(sorted_videos):
                ep_num = video_episode_map.get(video_path, 0)
                video_stem = Path(video_path).stem.lower()
                
                matched_subtitle = None
                for sub_path in subtitle_files:
                    if sub_path in used_subtitles:
                        continue
                    sub_stem = Path(sub_path).stem.lower()
                    if video_stem == sub_stem or video_stem in sub_stem or sub_stem in video_stem:
                        matched_subtitle = sub_path
                        used_subtitles.add(sub_path)
                        break
                    sub_ep_num = self.extract_episode_number(Path(sub_path).stem)
                    if ep_num > 0 and sub_ep_num > 0 and sub_ep_num == ep_num:
                        matched_subtitle = sub_path
                        used_subtitles.add(sub_path)
                        break
                
                episodes.append({
                    "episode_number": idx + 1,
                    "video_path": video_path,
                    "subtitle_path": matched_subtitle,
                    "video_filename": Path(video_path).name,
                    "subtitle_filename": Path(matched_subtitle).name if matched_subtitle else None
                })
            
            # 添加未匹配的字幕
            unmatched_subtitles = [sf for sf in subtitle_files if sf not in used_subtitles]
            for sub_path in sorted(unmatched_subtitles, key=lambda x: (subtitle_episode_map.get(x, 0), Path(x).stem.lower())):
                episodes.append({
                    "episode_number": len(episodes) + 1,
                    "video_path": None,
                    "subtitle_path": sub_path,
                    "video_filename": None,
                    "subtitle_filename": Path(sub_path).name
                })
        else:
            # 只有字幕
            sorted_subtitles = sorted(subtitle_files, key=lambda x: (subtitle_episode_map.get(x, 0), Path(x).stem.lower()))
            for idx, sub_path in enumerate(sorted_subtitles):
                episodes.append({
                    "episode_number": idx + 1,
                    "video_path": None,
                    "subtitle_path": sub_path,
                    "video_filename": None,
                    "subtitle_filename": Path(sub_path).name
                })
        
        # 重新编号
        for idx, ep in enumerate(episodes):
            ep["episode_number"] = idx + 1
        
        return episodes
