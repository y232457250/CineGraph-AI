import json
from pathlib import Path
from typing import List, Dict

DATA_FILE = Path(__file__).resolve().parents[2] / 'data' / 'media_index.json'


def ensure_data_dir():
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)


def save_movies(movies: List[Dict], *, merge_existing: bool = True) -> None:
    """Persist movie metadata to disk with optional merge behavior."""
    ensure_data_dir()

    existing_list: List[Dict] = load_movies() if merge_existing else []
    existing_map = {str(m.get("douban_id")): m for m in existing_list if m.get("douban_id")}

    normalized: List[Dict] = []
    new_ids = set()

    for m in movies:
        dbid = str(m.get("douban_id") or m.get("id") or "").strip()
        if not dbid:
            continue

        new_ids.add(dbid)
        source = existing_map.get(dbid, {}) if merge_existing else {}

        def pick(key: str, default=None):
            value = m.get(key)
            if value is None or value == "":
                return source.get(key, default)
            return value

        nm: Dict = {
            "douban_id": dbid,
            "title": pick("title"),
            "folder": pick("folder"),
            "video_path": pick("video_path"),
            "subtitle_path": pick("subtitle_path"),
            "video_count": pick("video_count", 1) or 0,
            "subtitle_count": pick("subtitle_count", 0) or 0,
            "media_type": pick("media_type", "movie"),
            "episodes": pick("episodes", []),
            "status": pick("status", "ready"),
        }

        for key in [
            "director",
            "writer",
            "starring",
            "genre",
            "country",
            "language",
            "release_date",
            "douban_url",
            "rating",
            "poster_url",
            "local_poster",
            "annotation_path",
            "status_import",
            "status_annotate",
            "status_vectorize",
        ]:
            val = pick(key)
            if val is not None:
                nm[key] = val

        normalized.append(nm)

    if merge_existing:
        for dbid, old_m in existing_map.items():
            if dbid not in new_ids:
                normalized.append(old_m)

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump({"movies": normalized}, f, ensure_ascii=False, indent=2)

def load_movies() -> List[Dict]:
    """Load movies metadata if exists, else return empty list."""
    if not DATA_FILE.exists():
        return []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('movies', [])
