from collections.abc import Iterator, Sequence
from datetime import datetime
from pathlib import Path
import re

import feedparser
import pandas as pd
from typing import Sequence
from sqlalchemy import insert, select, update, bindparam, Row
from sqlalchemy.engine.base import Engine
from db import metadata, channel_table, video_table
from download import download_thumbnail
from IPython.core.debugger import set_trace


VIDEO_ATTRIBUTES = [
    "yt_videoid",
    "title",
    "link",
    "media_thumbnail",
    "published",
]
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

class Backend:
    def __init__(self, engine: Engine, thumbnail_dir: str) -> None:
        self.engine = engine
        self.thumbnail_dir = thumbnail_dir
        Path(self.thumbnail_dir).mkdir(parents=True, exist_ok=True)

        metadata.drop_all(self.engine)
        metadata.create_all(self.engine)

        self.add_new_feeds(FEEDS)
        self.update_all_channels()

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

    def validate_thumbnail_paths(self) -> None:
        thumbnail_dir = Path(self.thumbnail_dir)
        if not thumbnail_dir.exists() or not thumbnail_dir.is_dir():
            raise FileNotFoundError(
                f"Thumbnails directory '{thumbnail_dir}' is not a directory or doesn't exists"
            )
        thumbnails = set(thumbnail_dir.iterdir())
        with self.engine.begin() as conn:
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
        self.validate_thumbnail_paths()
        for parsed_feed in self.download_feeds():
            if parsed_feed["status"] != 200:
                raise ConnectionError(f"feedparser exited with status {parsed_feed['status']}")
            self.update_channel(parsed_feed)
        self.download_thumbnails()

    def query_videos(self) -> Sequence[Row]:
        with self.engine.begin() as conn:
            stmt = (
                select(video_table, channel_table.c.title.label("channel_title"))
                .join(channel_table)
                .order_by(video_table.c.publication_dt)
            )
            query_result = conn.execute(
                select(video_table, channel_table.c.title.label("channel_title"))
                .join(channel_table)
                .order_by(video_table.c.publication_dt)
            )
        return query_result.all()
