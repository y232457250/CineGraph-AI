import os
import re
from pathlib import Path
from ...models.media import MediaItem

class MediaScanner:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        # 匹配数字(豆瓣ID) + 名字的正则
        self.folder_pattern = re.compile(r'^(\d+)\s*(.*)')

    def scan(self) -> List[MediaItem]:
        media_list = []
        
        # 遍历根目录下的第一层文件夹
        for folder in self.root_dir.iterdir():
            if folder.is_dir():
                match = self.folder_pattern.match(folder.name)
                if match:
                    douban_id = match.group(1)
                    title = match.group(2).strip()
                    
                    # 在文件夹内匹配视频和字幕
                    video_file = None
                    subtitle_file = None
                    
                    # 支持的后缀
                    video_exts = {'.mp4', '.mkv', '.avi', '.mov'}
                    sub_exts = {'.srt', '.ass', '.vtt'}
                    
                    for file in folder.iterdir():
                        if file.suffix.lower() in video_exts:
                            video_file = str(file)
                        elif file.suffix.lower() in sub_exts:
                            subtitle_file = str(file)
                    
                    if video_file and subtitle_file:
                        media_list.append(MediaItem(
                            douban_id=douban_id,
                            title=title,
                            video_path=video_file,
                            subtitle_path=subtitle_file
                        ))
        return media_list