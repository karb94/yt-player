from collections.abc import Iterable, Sequence, Collection
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
import re
import logging

import feedparser
import pandas as pd
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session
from sqlalchemy.engine.base import Engine

from db import Base, VideoTable, ChannelTable
from download import download_thumbnail, download_video

import gi
gi.require_version("Notify", "0.7")
from gi.repository import GLib, Notify

logger = logging.getLogger(__name__)

VIDEO_ATTRIBUTES = [
    "yt_videoid",
    "title",
    "published",
]
VIDEO_FORMAT = "mkv"
THUMBNAIL_FORMAT = "jpg"
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
    def __init__(
        self,
        engine: Engine,
        thumbnail_dir: str,
        video_dir: str,
        channel_ids: Collection[str],
    ) -> None:
        self.engine = engine

        # Create thumbnail directory
        thumbnail_dir_path = Path(thumbnail_dir)
        thumbnail_dir_path.mkdir(parents=True, exist_ok=True)
        self.thumbnail_dir = str(thumbnail_dir_path.absolute())
        logger.info(f'{self.thumbnail_dir=}')

        # Create video directory
        video_dir_path = Path(video_dir)
        video_dir_path.mkdir(parents=True, exist_ok=True)
        self.video_dir = str(video_dir_path.absolute())
        logger.info(f'{self.video_dir=}')

        self.channel_ids = set(channel_ids)
        logger.info(f'{self.channel_ids=}')

        # Recreate database tables
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)

        feed_urls = map(FEED_PREFIX.__add__, channel_ids)
        # feeds = FEEDS
        for feed_url in feed_urls:
            self.fetch_feed(feed_url)
        logger.info('Fetching feeds')
        self.delete_orphan_channels()
        self.clean_assets()
        logger.info('Backend successfully initialised')

    def update_fields(self, id: str, **kwargs: Any) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                update(VideoTable)
                .filter_by(id=id)
                .values(**kwargs)
            )

    def get_thumbnail_path(self, id: str) -> str:
        return str(Path(self.thumbnail_dir).absolute() / f"{id}.{THUMBNAIL_FORMAT}")

    def get_video_path(self, id: str) -> str:
        return str(Path(self.video_dir).absolute() / f"{id}.{VIDEO_FORMAT}")

    def add_new_videos(self, parsed_feed: Any) -> None:
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
                downloading=False,
                watched=False,
            )
            .sort_values("publication_dt")
            .iloc[:1]
        )
        logger.info(f"Writing {len(video_df)} videos to database")
        video_df.to_sql("video", self.engine, if_exists="append")

    def insert_channel(self, parsed_feed: Any) -> None:
        channel_id = extract_channel_id(parsed_feed.href)
        channel_title = parsed_feed.feed.title
        with Session(self.engine) as session:
            channel = ChannelTable(
                id=channel_id,
                title=channel_title,
                last_updated=datetime.now()
            )
            session.add(channel)
            session.commit()

    def delete_orphan_channels(self) -> None:
        """Delete channels from the database that are not included in `channel_ids`"""
        with Session(self.engine) as session:
            session.execute(
                delete(ChannelTable)
                .where(ChannelTable.id.not_in(self.channel_ids))
            )

    def fetch_feed(self, feed_url: str) -> None:
        parsed_feed = feedparser.parse(feed_url)
        logger.info(f'Parsing feed {parsed_feed.keys()}')
        if parsed_feed["status"] != 200:
            raise ConnectionError(f"feedparser exited with status {parsed_feed['status']}")
        self.insert_channel(parsed_feed)
        self.add_new_videos(parsed_feed)

    def clean_assets(self) -> None:
        """Delete videos and thumbnails from videos that either don't exist in the database or have been watched"""
        video_ids = tuple(self.query_video_ids(watched=False))
        for video_path in Path(self.video_dir).iterdir():
            if video_path.suffix != VIDEO_FORMAT:
                video_path.unlink()
            if video_path.stem not in video_ids:
                video_path.unlink()
        for thumbnail_path in Path(self.thumbnail_dir).iterdir():
            if thumbnail_path.suffix != THUMBNAIL_FORMAT:
                thumbnail_path.unlink()
            if thumbnail_path.stem not in video_ids:
                thumbnail_path.unlink()

    def query_video_ids(self, **kwargs: Any) -> Sequence[str]:
        with Session(self.engine) as session:
            query_result = session.scalars(
                select(VideoTable.id)
                .order_by(VideoTable.publication_dt.desc())
                .filter_by(**kwargs)
            )
        return query_result.all()

    def create_notification(self, id: str) -> Notify.Notification:
        Notify.init()
        with Session(self.engine) as session:
            title = session.scalar(select(VideoTable.title).filter_by(id=id))
        thumbnail_path = str(Path(self.thumbnail_dir).absolute() / f"{id}.{THUMBNAIL_FORMAT}")
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

    def download_video(self, id: str, with_notification: bool, **ytdlp_kwargs: Any) -> None:
        self.update_fields(id, downloading=True)
        notification = self.create_notification(id) if with_notification else None
        output_format = VIDEO_FORMAT
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

    def delete_video_assets(self, id: str) -> None:
        video_path = self.get_video_path(id)
        Path(video_path).unlink(missing_ok=True)
        thumbnail_path = self.get_thumbnail_path(id)
        Path(thumbnail_path).unlink(missing_ok=True)

    def delete_video(self, id: str) -> None:
        self.delete_video_assets(id)
        with Session(self.engine) as session:
            session.execute(
                delete(VideoTable)
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

    def __post_init__(self) -> None:
        self.path = self.backend.get_video_path(self.id)
        self.thumbnail_path = self.backend.get_thumbnail_path(self.id)

    def download(self, **kwargs: Any) -> None:
        self.backend.download_video(self.id, **kwargs)

    @property
    def downloaded(self) -> bool:
        return Path(self.path).is_file()

    @property
    def downloading(self) -> bool | None:
        with Session(self.backend.engine) as session:
            return session.scalar(
                select(VideoTable.downloading)
                .filter_by(id=id)
            )

    @property
    def thumbnail_downloaded(self) -> bool:
        return Path(self.thumbnail_path).is_file()

    def download_thumbnail(self) -> None:
        if not self.thumbnail_downloaded:
            download_thumbnail(self.id, self.thumbnail_path)

    @property
    def watched(self) -> bool | None:
        with Session(self.backend.engine) as session:
            return session.scalar(
                select(VideoTable.watched)
                .filter_by(id=id)
            )

    @watched.setter
    def watched(self, value: bool) -> None:
        with Session(self.backend.engine) as session:
            session.execute(
                update(VideoTable)
                .filter_by(id=self.id)
                .values(watched=value)
            )
            self.delete_assets()

    def delete_assets(self) -> None:
        self.backend.delete_video_assets(self.id)

    def delete(self) -> None:
        self.backend.delete_video(self.id)

