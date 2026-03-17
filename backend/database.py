import os
import sqlite3
from datetime import datetime

DB_PATH = "data/metadata.db"


def _connect() -> sqlite3.Connection:
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the media table if it does not already exist."""
    conn = _connect()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS images (
            image_id        TEXT PRIMARY KEY,
            file_path       TEXT NOT NULL,
            original_name   TEXT NOT NULL,
            caption         TEXT,
            upload_ts       TEXT NOT NULL,
            file_size       INTEGER,
            width           INTEGER,
            height          INTEGER,
            media_type      TEXT DEFAULT 'image'
        )
        """
    )
    conn.commit()
    conn.close()
    
    # Migrate: add media_type column if not exists
    try:
        conn = _connect()
        conn.execute("ALTER TABLE images ADD COLUMN media_type TEXT DEFAULT 'image'")
        conn.commit()
        conn.close()
    except Exception:
        pass  # Column already exists


def insert_image(
    image_id: str,
    file_path: str,
    original_name: str,
    caption: str,
    file_size: int | None = None,
    width: int | None = None,
    height: int | None = None,
    media_type: str = "image",
):
    conn = _connect()
    conn.execute(
        """
        INSERT INTO images
            (image_id, file_path, original_name, caption, upload_ts, file_size, width, height, media_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            image_id,
            file_path,
            original_name,
            caption,
            datetime.now().isoformat(timespec="seconds"),
            file_size,
            width,
            height,
            media_type,
        ),
    )
    conn.commit()
    conn.close()


def get_image_by_id(image_id: str) -> dict | None:
    conn = _connect()
    row = conn.execute(
        "SELECT * FROM images WHERE image_id = ?", (image_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_images() -> list[dict]:
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM images ORDER BY upload_ts DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_image(image_id: str):
    conn = _connect()
    conn.execute("DELETE FROM images WHERE image_id = ?", (image_id,))
    conn.commit()
    conn.close()


def get_image_count() -> int:
    conn = _connect()
    count = conn.execute("SELECT COUNT(*) FROM images").fetchone()[0]
    conn.close()
    return count
