from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re

import feedparser
import pandas as pd
from sqlalchemy import delete, insert, select, update
from sqlalchemy.orm import Session
from sqlalchemy.engine.base import Engine

from db import channel_table, video_table, metadata, VideoTable, ChannelTable
from download import download_thumbnail, download_video

import gi
gi.require_version("Notify", "0.7")
from gi.repository import GLib, Notify # type: ignore[attr-defined]



VIDEO_ATTRIBUTES = [
    "yt_videoid",
    "title",
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
    def __init__(self, engine: Engine, thumbnail_dir: str, video_dir: str) -> None:
        self.engine = engine
        thumbnail_dir_path = Path(thumbnail_dir)
        thumbnail_dir_path.mkdir(parents=True, exist_ok=True)
        self.thumbnail_dir = str(thumbnail_dir_path.absolute())
        video_dir_path = Path(video_dir)
        video_dir_path.mkdir(parents=True, exist_ok=True)
        self.video_dir = str(video_dir_path.absolute())

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

    def get_thumbnail_path(self, id: str) -> str:
        return str(Path(self.thumbnail_dir).absolute() / f"{id}.jpg")

    def get_video_path(self, id: str) -> str:
        return str(Path(self.video_dir).absolute() / f"{id}.mkv")

    def add_new_feeds(self, feeds: list[str]) -> None:
        channel_ids = set(map(extract_channel_id, feeds))
        with self.engine.begin() as conn:
            query_result = conn.execute(select(channel_table.c.id))
            db_channel_ids = set(query_result.scalars().all())
            missing_channel_ids = channel_ids - db_channel_ids
            if missing_channel_ids:
                values = [dict(id=channel_id) for channel_id in missing_channel_ids]
                conn.execute(insert(channel_table), values)

    def download_feeds(self) -> Iterator:
        with Session(self.engine) as session:
            channel_ids = session.scalars(select(ChannelTable.id))
        feeds = map(FEED_PREFIX.__add__, channel_ids)
        return map(feedparser.parse, feeds)

    def add_new_videos(self, parsed_feed) -> None:
        channel_id = extract_channel_id(parsed_feed.href)
        db_video_ids = set(self.query_video_ids())
        video_df = pd.DataFrame(data=parsed_feed.entries, columns=VIDEO_ATTRIBUTES)
        missing_video_ids = list(set(video_df["yt_videoid"]) - db_video_ids)
        video_df = (
            video_df
            .rename(columns={
                "yt_videoid": "id",
                "published": "publication_dt",
            })
            .set_index("id")
            .loc[missing_video_ids]
            .assign(
                publication_dt=lambda df: pd.to_datetime(df["publication_dt"]),
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
                update(ChannelTable)
                .where(ChannelTable.id == channel_id)
                .values(title=channel_title, last_updated=datetime.now())
            )
        self.add_new_videos(parsed_feed)

    def download_thumbnails(self) -> None:
        for video_id in self.query_video_ids():
            download_thumbnail(video_id, self.thumbnail_dir)

    def update_all_channels(self) -> None:
        for parsed_feed in self.download_feeds():
            if parsed_feed["status"] != 200:
                raise ConnectionError(f"feedparser exited with status {parsed_feed['status']}")
            self.update_channel(parsed_feed)

    def query_videos(self) -> Sequence[VideoTable]:
        with Session(self.engine) as session:
            query_result = session.scalars(
                select(VideoTable)
                .order_by(video_table.c.publication_dt.desc())
            )
        return query_result.all()

    def query_video_ids(self) -> Sequence[str]:
        with Session(self.engine) as session:
            query_result = session.scalars(
                select(VideoTable.id)
                .order_by(VideoTable.publication_dt.desc())
            )
        return query_result.all()

    def create_notification(self, id: str) -> Notify.Notification:
        Notify.init()
        title = self.get_field(id=id, field="title")
        thumbnail_path = str(Path(self.thumbnail_dir).absolute() / f"{id}.jpg")
        with Session(self.engine) as session:
            channel_title = session.scalar(
                select(ChannelTable.title)
                .join(VideoTable)
                .where(VideoTable.id == id)
            )
        if channel_title is None:
            raise ValueError(f"Video with id {id} does not exist in the database")
        notification = Notify.Notification.new(channel_title, title, thumbnail_path)
        notification.set_timeout(Notify.EXPIRES_NEVER)
        notification.set_app_name("yt-player")
        tag = GLib.Variant.new_string(id)
        notification.set_hint("x-dunst-stack-tag", tag)
        return notification

    def download_video(self, id: str, with_notification: bool, **ytdlp_kwargs):
        self.update_fields(id, downloading=True)
        notification = self.create_notification(id) if with_notification else None
        output_format = "mkv"
        filename = f"{id}.{output_format}"
        video_path = str(Path(self.video_dir) / filename)
        ytdlp_kwargs["merge_output_format"] = output_format
        ytdlp_kwargs["noprogress"] = output_format

        download_video(
            url=id,
            path=video_path,
            notification=notification,
            **ytdlp_kwargs,
        )
        self.update_fields(id, downloading=False)

    def create_video(self, id: str) -> "Video":
        with Session(self.engine) as session:
            video = session.scalar(
                select(VideoTable)
                .filter_by(id=id)
            )
            if video is None:
                raise ValueError(f"Video with id {id} does not exists in the database")
            return Video(
                backend=self,
                id=video.id,
                publication_dt=video.publication_dt,
                title=video.title,
                channel_id=video.channel.id,
                channel_title=video.channel.title,
            )

    def delete_video(self, id: str) -> None:
        video_path = self.get_field(id, "path")
        if video_path is not None:
            Path(video_path).unlink(missing_ok=True)
        thumbnail_path = self.get_field(id, "thumbnail_path")
        if thumbnail_path is not None:
            Path(thumbnail_path).unlink(missing_ok=True)
        with self.engine.begin() as conn:
            conn.execute(
                delete(video_table)
                .filter_by(id=id)
            )


@dataclass
class Video:
    backend: Backend
    id: str
    publication_dt: datetime
    title: str
    channel_id: str
    channel_title: str

    def __post_init__(self):
        self.path = self.backend.get_video_path(self.id)
        self.thumbnail_path = self.backend.get_thumbnail_path(self.id)

    def download(self, **kwargs) -> None:
        self.backend.download_video(self.id, **kwargs)

    @property
    def downloaded(self) -> bool:
        return Path(self.path).is_file()

    @property
    def downloading(self) -> bool | None:
        return self.backend.get_field(self.id, "downloaded")

    @property
    def thumbnail_downloaded(self) -> bool:
        return Path(self.thumbnail_path).is_file()

    def download_thumbnail(self) -> None:
        if not self.thumbnail_downloaded:
            download_thumbnail(self.id, self.thumbnail_path)

    @property
    def read(self) -> bool | None:
        return self.backend.get_field(self.id, "read")

    def delete(self) -> None:
        self.backend.delete_video(self.id)

