from sqlalchemy.engine.base import Engine
from sqlalchemy import select, update, bindparam
# from yt_dlp import YoutubeDL
from db import video_table
# from IPython.core.debugger import set_trace
from urllib.request import urlretrieve
from pathlib import Path

formats_ranking = (
    "bestvideo[width=2560][vcodec=vp9]+bestaudio",
    "bestvideo[width=2560]+bestaudio",
    "bestvideo[width<=2560]+bestaudio",
    "best",
)
OPTIONS = {
    "format": "/".join(formats_ranking)
}
# https://github.com/yt-dlp/yt-dlp/blob/b6951271ac014761c9c317b9cecd5e8e139cfa7c/yt_dlp/utils/_utils.py#L2781
OUTTMPL_TYPES = {
    'pl_video': "%(id)s.%(ext)s",
}
MERGE_OUTPUT_FORMAT = "mkv"

url = "https://www.youtube.com/watch?v=xSqol6GQRJw.jpg"

# def download_video(url: str):
#     with YoutubeDL() as ydl:
#         error_code = ydl.download(url)


def download_thumbnail(url: str, video_id: str, dir: str) -> str:
    thumbnail_dir = Path(dir)
    thumbnail_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(url).suffix
    filename = video_id + ext
    thumbnail_path = thumbnail_dir / filename
    urlretrieve(url, thumbnail_path)
    return str(thumbnail_path)


def download_thumbnails(engine: Engine, dir: str):
    with engine.begin() as conn:
        query_result = conn.execute(
            select(video_table.c["id", "thumbnail_url"])
            .where(video_table.c.thumbnail_path.is_(None))
        )
        for video_id, thumbnail_url in query_result:
            thumbnail_path = download_thumbnail(thumbnail_url, video_id, dir)
            conn.execute(
                update(video_table)
                .filter_by(id=video_id)
                .values(thumbnail_path=thumbnail_path)
            )


def validate_thumbnail_paths(engine: Engine, dir: str):
    thumbnail_dir = Path(dir)
    thumbnails = set(thumbnail_dir.iterdir())
    with engine.begin() as conn:
        query_result = conn.execute(
            select(video_table.c["thumbnail_path"])
            .where(video_table.c.thumbnail_path.is_not(None))
        )
        db_paths = set(Path(path) for path in query_result.scalars())
        existing_thumbnails = thumbnails - db_paths
        if existing_thumbnails:
            update_stmt = (
                update(video_table)
                .filter_by(id=bindparam("video_id"))
                .values(thumbnail_path=bindparam("thumbnail_path"))
            )
            values = [
                dict(video_id=path.stem, thumbnail_path=str(path))
                for path in existing_thumbnails
            ]
            conn.execute(update_stmt, values)
        missing_thumbnails = db_paths - thumbnails
        if missing_thumbnails:
            update_stmt = (
                update(video_table)
                .filter_by(id=bindparam("video_id"))
                .values(thumbnail_path=None)
            )
            values = [dict(video_id=path.stem) for path in missing_thumbnails]
            conn.execute(update_stmt, values)

