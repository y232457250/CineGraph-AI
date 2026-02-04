#!/usr/bin/env python3
"""enrich_from_douban.py

读取 `backend/data/media_index.json`，根据每条记录的 `douban_id` 抓取豆瓣页面并提取：
  - director, writer, cast, genres, country, language, release_date, douban_url
将结果写入 `backend/data/media_index_enriched.json`（覆盖/创建）。

用法示例：
  python backend/scripts/enrich_from_douban.py --input backend/data/media_index.json --output backend/data/media_index_enriched.json

支持参数：--delay（请求间隔秒），--start（从第几条开始），--limit
"""
import argparse
import json
import time
from pathlib import Path
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def make_session(retries: int = 3, backoff: float = 0.5, timeout: int = 8):
    s = requests.Session()
    retries_obj = Retry(total=retries, backoff_factor=backoff, status_forcelist=[429, 500, 502, 503, 504])
    s.mount('https://', HTTPAdapter(max_retries=retries_obj))
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
    })
    s.request_timeout = timeout
    return s


def normalize_language(languages: list) -> str:
    """将语言列表简化为：中文、英文、其他、或组合"""
    if not languages:
        return "其他"
    
    # 中文相关的语言
    chinese_keywords = ['汉语', '普通话', '国语', '粤语', '闽南语', '上海话', '四川话', 
                        '陕西话', '东北话', '南京话', '吴语', '客家话', '方言', '中文',
                        '台语', '潮汕话', '湖南话', '河南话', '山东话', '云南方言']
    # 英文相关的语言
    english_keywords = ['英语', 'English', '英文']
    
    has_chinese = False
    has_english = False
    
    lang_str = " ".join(languages).lower()
    
    for kw in chinese_keywords:
        if kw.lower() in lang_str:
            has_chinese = True
            break
    
    for kw in english_keywords:
        if kw.lower() in lang_str:
            has_english = True
            break
    
    if has_chinese and has_english:
        return "中文 / 英文"
    elif has_chinese:
        return "中文"
    elif has_english:
        return "英文"
    else:
        return "其他"


def fetch_douban(session: requests.Session, douban_id: str, timeout: int = 8) -> Optional[dict]:
    """Fetch movie details using Douban's Rexxar API (mobile API)."""
    base_url = f'https://m.douban.com/rexxar/api/v2/movie/{douban_id}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1',
        'Referer': f'https://m.douban.com/movie/subject/{douban_id}/',
    }
    params = {'ck': '', 'for_mobile': '1'}
    
    try:
        # 1. Get basic info
        resp = session.get(base_url, headers=headers, params=params, timeout=timeout)
        if resp.status_code != 200:
            print(f'WARN: douban {douban_id} returned {resp.status_code}')
            return None
        
        data = resp.json()
        
        # 获取演员列表，只取前4个
        actors = [a['name'] for a in data.get('actors', [])][:4]
        
        info = {
            'title': data.get('title'),
            'genre': " / ".join(data.get('genres', [])),
            'country': " / ".join(data.get('countries', [])),
            'language': normalize_language(data.get('languages', [])),
            'release_date': data.get('pubdate', [None])[0],
            'director': ", ".join([d['name'] for d in data.get('directors', [])]),
            'starring': actors,
            'writer': None,
            'douban_url': f'https://movie.douban.com/subject/{douban_id}/',
            'poster_url': data.get('pic', {}).get('large') or data.get('cover_url') or data.get('cover', {}).get('url'),
            'rating': str(data.get('rating', {}).get('value', '')) if data.get('rating', {}).get('value') else None
        }
        
        # 2. Get credits for writers (not in main subject API)
        credits_url = f'{base_url}/credits'
        c_resp = session.get(credits_url, headers=headers, timeout=timeout)
        if c_resp.status_code == 200:
            c_data = c_resp.json()
            writers = []
            seen_writers = set()
            for item in c_data.get('items', []):
                if item.get('category') == '编剧':
                    name = item.get('name')
                    if name and name not in seen_writers:
                        writers.append(name)
                        seen_writers.add(name)
            info['writer'] = ", ".join(writers) if writers else None
            
            # Fallback for starring if main API actors list is empty
            if not info['starring']:
                actors = []
                for item in c_data.get('items', []):
                    if item.get('category') == '演员':
                        name = item.get('name')
                        if name: actors.append(name)
                info['starring'] = actors[:4]
        
        return info
    except Exception as e:
        print(f'ERROR fetching douban Rexxar {douban_id}: {e}')
        return None


def enrich(input_path: Path, output_path: Path, delay: float = 0.5, start: int = 0, limit: Optional[int] = None, proxies: Optional[dict] = None, media_base_path: Optional[Path] = None):
    session = make_session()
    if proxies:
        session.proxies.update(proxies)

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    movies = data.get('movies', [])
    total = len(movies)
    end = total if limit is None else min(total, start + limit)

    print(f'Starting enrichment: {start}..{end} of {total} (delay={delay}s)')
    if media_base_path:
        print(f'Media base path: {media_base_path}')

    for i in range(start, end):
        m = movies[i]
        douban_id = m.get('douban_id') or m.get('id')
        print(f'[{i+1}/{end}] id={douban_id} title={m.get("title")}')
        
        # Ensure fields exist initially with default types
        for k, v in {
            'director': None, 'writer': None, 'starring': [], 
            'genre': None, 'country': None, 'language': None, 
            'release_date': None
        }.items():
            if k not in m:
                m[k] = v

        if not douban_id:
            print('  -> no douban_id, skip')
            continue
        meta = fetch_douban(session, str(douban_id))
        if meta:
            # merge
            for k, v in meta.items():
                if v: # Only overwrite if we got a value
                    m[k] = v
            
            # 下载海报图片到本地
            poster_url = meta.get('poster_url')
            if poster_url and media_base_path:
                folder_name = m.get('folder')
                if folder_name:
                    movie_folder = media_base_path / folder_name
                    if movie_folder.exists():
                        local_poster = download_poster(session, poster_url, movie_folder, str(douban_id))
                        if local_poster:
                            m['local_poster'] = local_poster
                            print(f'  -> poster saved')
            
            print('  -> fetched')
        else:
            print('  -> fetch failed')
        # incremental save
        with open(output_path, 'w', encoding='utf-8') as out:
            json.dump({'movies': movies}, out, ensure_ascii=False, indent=2)
        time.sleep(delay)

    print('Enrichment finished. Output:', output_path)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', '-i', default='backend/data/media_index.json')
    p.add_argument('--output', '-o', default='backend/data/media_index_enriched.json')
    p.add_argument('--delay', type=float, default=0.5)
    p.add_argument('--start', type=int, default=0)
    p.add_argument('--limit', type=int, default=None)
    p.add_argument('--proxy', type=str, default=None, help='http proxy URL, e.g. http://127.0.0.1:7890')
    p.add_argument('--media-path', '-m', type=str, default=None, help='影片文件夹的基础路径，用于下载海报到对应电影目录')
    args = p.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    proxies = None
    if args.proxy:
        proxies = {'http': args.proxy, 'https': args.proxy}
    
    media_base_path = Path(args.media_path) if args.media_path else None

    enrich(input_path, output_path, delay=args.delay, start=args.start, limit=args.limit, proxies=proxies, media_base_path=media_base_path)


if __name__ == '__main__':
    main()
