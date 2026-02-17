#!/usr/bin/env python3
"""
add_meme.py

Usage:
    python add_meme.py /path/to/image.jpg memes
    python add_meme.py /path/to/image.png calm

Behavior:
- Copies the given image into media/memes/ or media/calm/
- Auto-renames to positive_001.jpg, positive_002.jpg, ... or calm_001.jpg, ...
- Logs the entry to meme_library.db (SQLite) with columns:
    id, filename, category, original_name, added_at

Standard library only.
"""

import argparse
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
import re
import sys

DB_NAME = "meme_library.db"
MEDIA_DIR = Path("media")
CATEGORY_MAP = {
    "memes": {"subdir": "memes", "prefix": "positive"},
    "calm": {"subdir": "calm", "prefix": "calm"},
}


def init_db(db_path: Path):
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS meme_library (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            category TEXT NOT NULL,
            original_name TEXT NOT NULL,
            added_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def next_filename(dest_dir: Path, prefix: str, ext: str) -> str:
    """Find next available filename like prefix_001.ext"""
    pattern = re.compile(rf"^{re.escape(prefix)}_(\d{{3}})\{re.escape(ext)}$", re.IGNORECASE)
    max_idx = 0
    for p in dest_dir.iterdir():
        if not p.is_file():
            continue
        m = pattern.match(p.name)
        if m:
            try:
                idx = int(m.group(1))
                if idx > max_idx:
                    max_idx = idx
            except ValueError:
                continue
    next_idx = max_idx + 1
    return f"{prefix}_{next_idx:03d}{ext}"


def copy_and_register(src_path: Path, category: str):
    if category not in CATEGORY_MAP:
        raise ValueError(f"Invalid category: {category}. Must be one of: {', '.join(CATEGORY_MAP.keys())}")

    src_path = src_path.expanduser().resolve()
    if not src_path.exists() or not src_path.is_file():
        raise FileNotFoundError(f"Source file not found: {src_path}")

    info = CATEGORY_MAP[category]
    dest_dir = MEDIA_DIR / info["subdir"]
    dest_dir.mkdir(parents=True, exist_ok=True)

    ext = src_path.suffix.lower()
    if not ext:
        ext = ".jpg"

    # sanitize extension to common image types, default to .jpg
    if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        ext = ".jpg"

    prefix = info["prefix"]

    new_name = next_filename(dest_dir, prefix, ext)
    dest_path = dest_dir / new_name

    # Ensure unique (in very rare race)
    while dest_path.exists():
        # increment
        m = re.search(r"_(\d{3})\.", dest_path.name)
        if m:
            idx = int(m.group(1)) + 1
        else:
            idx = 1
        new_name = f"{prefix}_{idx:03d}{ext}"
        dest_path = dest_dir / new_name

    shutil.copy2(str(src_path), str(dest_path))

    # Insert into DB
    db_path = Path(DB_NAME)
    conn = init_db(db_path)
    cur = conn.cursor()
    added_at = datetime.utcnow().isoformat() + "Z"
    cur.execute(
        "INSERT INTO meme_library (filename, category, original_name, added_at) VALUES (?, ?, ?, ?)",
        (new_name, category, src_path.name, added_at),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()

    return new_id, dest_path, new_name


def main(argv=None):
    parser = argparse.ArgumentParser(description="Add an image to media library and register in DB")
    parser.add_argument("file", help="Path to image file to add")
    parser.add_argument("category", choices=list(CATEGORY_MAP.keys()), help="Category: memes or calm")
    args = parser.parse_args(argv)

    try:
        new_id, dest_path, new_name = copy_and_register(Path(args.file), args.category)
        print("Added:")
        print(f"  id: {new_id}")
        print(f"  filename: {new_name}")
        print(f"  path: {dest_path}")
        print(f"  category: {args.category}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
