from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from os.path import isfile
from pathlib import Path
import re

import feedparser
import pandas as pd
from typing import Any, Sequence
from sqlalchemy import insert, select, update, bindparam, Row
from sqlalchemy.engine.base import Engine
from db import metadata, channel_table, video_table
from download import download_thumbnail, download_video
from IPython.core.debugger import set_trace
from threading import Thread
from yt_dlp import YoutubeDL
from urllib.request import urlretrieve
from pprint import pp
from collections.abc import Callable


VIDEO_ATTRIBUTES = [
    "yt_videoid",
    "title",
    "link",
    "media_thumbnail",
    "published",
]
FORMATS_RANKING = (
    "bestvideo[width=2560][vcodec=vp09.00.50.08][ext=mp4]+bestaudio",
    "bestvideo[width=2560][vcodec=vp9][ext=mp4]+bestaudio",
    "bestvideo[width=2560][vcodec=vp09.00.50.08]+bestaudio",
    "bestvideo[width=2560]+bestaudio",
    "bestvideo[width<=2560]+bestaudio",
    "best",
)
FEED_PREFIX = "https://www.youtube.com/feeds/videos.xml?channel_id="
channel_id_regex = re.compile(re.escape(FEED_PREFIX) + r"([\w-]{24})")
FEEDS = [
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCXuqSBlHAE6Xw-yeJA0Tunw",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCBJycsmduvYEL83R_U4JriQ",
]


def extract_channel_id(feed: str) -> str:
    match = channel_id_regex.fullmatch(feed)
    if match is None:
        raise ValueError("RSS feed doesn't match Youtube's RSS feed format")
    else:
        return match.group(1)


get_thumbnail_url = "http://img.youtube.com/vi/{video_id}/mqdefault.jpg".format


def download_thumbnail(video_id: str, dir: str) -> str:
    thumbnail_dir = Path(dir)
    thumbnail_dir.mkdir(parents=True, exist_ok=True)
    url = get_thumbnail_url(video_id=video_id)
    ext = Path(url).suffix
    filename = video_id + ext
    thumbnail_path = thumbnail_dir / filename
    urlretrieve(url, thumbnail_path)
    return str(thumbnail_path)


class Backend:
    def __init__(self, engine: Engine, thumbnail_dir: str, video_dir: str) -> None:
        self.engine = engine
        self.thumbnail_dir = thumbnail_dir
        Path(self.thumbnail_dir).mkdir(parents=True, exist_ok=True)
        self.video_dir = video_dir
        Path(self.video_dir).mkdir(parents=True, exist_ok=True)

        metadata.drop_all(self.engine)
        metadata.create_all(self.engine)

        self.add_new_feeds(FEEDS)
        self.update_all_channels()

    def get_field(self, id: str, field: str):
        with self.engine.begin() as conn:
            query_result = conn.execute(
                select(video_table.c[field])
                .filter_by(id=id)
            )
            return query_result.scalar_one_or_none()

    def update_fields(self, id: str, **kwargs):
        with self.engine.begin() as conn:
            conn.execute(
                update(video_table)
                .filter_by(id=id)
                .values(**kwargs)
            )

    def add_new_feeds(self, feeds: list[str]) -> None:
        channel_ids = set(map(extract_channel_id, feeds))
        with self.engine.begin() as conn:
            query_result = conn.execute(select(channel_table.c.id))
            db_channel_ids = set(query_result.scalars().all())
            missing_channel_ids = channel_ids - db_channel_ids
            values = [dict(id=channel_id) for channel_id in missing_channel_ids]
            conn.execute(insert(channel_table), values)

    def download_feeds(self) -> Iterator:
        with self.engine.begin() as conn:
            query_result = conn.execute(select(channel_table.c.id))
            channel_ids = set(query_result.scalars().all())
        feeds = [FEED_PREFIX + channel_id for channel_id in  channel_ids]
        return map(feedparser.parse, feeds)

    def add_new_videos(self, parsed_feed) -> None:
        channel_id = extract_channel_id(parsed_feed.href)
        with self.engine.begin() as conn:
            query_result = conn.execute(
                select(channel_table.c.id)
                .filter_by(id=channel_id)
            )
            db_video_ids = set(query_result.scalars())

        video_df = pd.DataFrame(data=parsed_feed.entries, columns=VIDEO_ATTRIBUTES)
        missing_video_ids = list(set(video_df["yt_videoid"]) - db_video_ids)
        video_df = (
            video_df
            .rename(columns={
                "yt_videoid": "id",
                "link": "url",
                "media_thumbnail": "thumbnail_url",
                "published": "publication_dt",
            })
            .set_index("id")
            .loc[missing_video_ids]
            .assign(
                publication_dt=lambda df: pd.to_datetime(df["publication_dt"]),
                thumbnail_url=lambda df: df["thumbnail_url"].map(lambda x: x[0]["url"]),
                channel_id=channel_id,
            )
            .sort_values("publication_dt")
        )
        video_df.to_sql("video", self.engine, if_exists="append")

    def update_channel(self, parsed_feed) -> None:
        channel_id = extract_channel_id(parsed_feed.href)
        channel_title = parsed_feed.feed.title
        with self.engine.begin() as conn:
            conn.execute(
                update(channel_table)
                .where(channel_table.c.id == channel_id)
                .values(title=channel_title, last_updated=datetime.now())
            )
        self.add_new_videos(parsed_feed)

    def validate_paths(self, dir_str: str, path_col: str) -> None:
        dir = Path(dir_str)
        if not dir.exists() or not dir.is_dir():
            raise FileNotFoundError(
                f"Directory '{dir}' is not a directory or doesn't exists"
            )
        files = set(dir.iterdir())
        with self.engine.begin() as conn:
            query_result = conn.execute(
                select(video_table.c[path_col])
                .where(video_table.c[path_col].is_not(None))
            )
            db_paths = set(Path(path) for path in query_result.scalars())
            db_ids = set(conn.execute(select(video_table.c.id)).scalars())

            existing_files = files - db_paths
            files_in_db = [path for path in existing_files if path.stem in db_ids]
            if files_in_db:
                update_stmt = (
                    update(video_table)
                    .filter_by(id=bindparam("video_id"))
                    .values(**{path_col: bindparam(path_col)})
                )
                values = [
                    {"video_id": path.stem, path_col: str(path)}
                    for path in existing_files
                ]
                conn.execute(update_stmt, values)

            for path in existing_files:
                if path.stem not in db_ids:
                    path.unlink()

            missing_files = db_paths - files
            if missing_files:
                update_stmt = (
                    update(video_table)
                    .filter_by(id=bindparam("video_id"))
                    .values(**{path_col: None})
                )
                values = [dict(video_id=path.stem) for path in missing_files]
                conn.execute(update_stmt, values)

    def download_thumbnails(self) -> None:
        with self.engine.begin() as conn:
            query_result = conn.execute(
                select(video_table.c["id", "thumbnail_url"])
                .where(video_table.c.thumbnail_path.is_(None))
            )
            for video_id, thumbnail_url in query_result:
                thumbnail_path = download_thumbnail(video_id, self.thumbnail_dir)
                conn.execute(
                    update(video_table)
                    .filter_by(id=video_id)
                    .values(thumbnail_path=thumbnail_path)
                )

    def update_all_channels(self) -> None:
        self.validate_paths(dir_str=self.thumbnail_dir, path_col="thumbnail_path")
        self.validate_paths(dir_str=self.video_dir, path_col="path")
        for parsed_feed in self.download_feeds():
            if parsed_feed["status"] != 200:
                raise ConnectionError(f"feedparser exited with status {parsed_feed['status']}")
            self.update_channel(parsed_feed)
        self.download_thumbnails()

    def query_videos(self) -> Sequence[Row]:
        with self.engine.begin() as conn:
            query_result = conn.execute(
                select(video_table, channel_table.c.title.label("channel_title"))
                .join(channel_table)
                .order_by(video_table.c.publication_dt.desc())
            )
        return query_result.all()

    def query_video_ids(self) -> Sequence[str]:
        with self.engine.begin() as conn:
            query_result = conn.execute(
                select(video_table.c.id)
                .order_by(video_table.c.publication_dt.desc())
            )
        return query_result.scalars().all()

    def download_video(self, id: str, **kwargs):
        with self.engine.begin() as conn:
            query_result = conn.execute(
                select(video_table.c.url)
                .filter_by(id=id)
            )
            url = query_result.scalar_one_or_none()
        if url is None:
            raise ValueError(f"No video with id {id} exists")
        ext = "mkv"
        video_path = f"{self.video_dir}/{id}.{ext}"
        options = {
            "format": "/".join(FORMATS_RANKING),
            "outtmpl": dict(default=video_path),
            "merge_output_format": ext,
            "noprogress": True,
        }
        options.update(kwargs)
        with YoutubeDL(options) as ydl:
            error_code = ydl.download(url)
        if error_code != 0:
            raise ConnectionError(f"Download of video with id {id} failed")
        if not Path(video_path).is_file():
            raise FileNotFoundError("Video was downloaded but file is not there")
        with self.engine.begin() as conn:
            conn.execute(
                update(video_table)
                .filter_by(id=id)
                .values(path=video_path)
            )

    def create_video(self, id: str) -> "Video":
        dynamic_fields = (
            "path",
            "thumbnail_path",
            "downloading",
            "downloaded",
        )
        video_columns = [col for col in video_table.c if col.name not in dynamic_fields]
        with self.engine.begin() as conn:
            query_result = conn.execute(
                select(*video_columns, channel_table.c.title.label("channel_title"))
                .join(channel_table)
                .where(video_table.c.id == id)
            )
            result = query_result.one_or_none()
        if result is None:
            raise ValueError(f"Video with id {id} does not exists in the database")
        return Video(backend=self, **result._mapping)


@dataclass
class Video:
    backend: Backend
    id: str
    url: str
    publication_dt: datetime
    title: str
    thumbnail_url: str
    channel_id: str
    channel_title: str

    @property
    def path(self) -> str | None:
        return self.backend.get_field(self.id, "path")

    @property
    def thumbnail_path(self) -> str | None:
        return self.backend.get_field(self.id, "thumbnail_path")

    @property
    def downloaded(self) -> str | None:
        return self.backend.get_field(self.id, "downloaded")

    @property
    def downloading(self) -> str | None:
        return self.backend.get_field(self.id, "downloaded")

    def download(self, **kwargs):
        self.backend.update_fields(self.id, downloading=True, downloaded=False)
        self.backend.download_video(self.id, **kwargs)
        self.backend.update_fields(self.id, downloading=False, downloaded=True)

