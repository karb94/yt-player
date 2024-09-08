import asyncio
import aiofiles
from collections.abc import Callable, Sequence
from dataclasses import InitVar, dataclass, field
from datetime import datetime
from time import mktime, struct_time
from pathlib import Path
from typing import Any, TypedDict, Iterable, Optional
import re
import logging

from aiohttp.client import ClientSession
import yrp.config as config

import feedparser
from sqlalchemy import delete, select, update, insert

from yrp import db as db
from yrp.download import download_video
from yrp.observer import Observable, Observable
import aiohttp

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


def get_thumbnail_path(id: str) -> Path:
    return config.thumbnail_dir.absolute() / f"{id}.{THUMBNAIL_FORMAT}"


def get_video_path(id: str) -> Path:
    return config.video_dir.absolute() / f"{id}.{VIDEO_FORMAT}"


def update_channels(channel_ids: set[str]) -> None:
    with db.Session.begin() as session:
        query_result = session.scalars(select(db.Channel.id))
        existing_channel_ids = set(query_result)
        unused_channel_ids = existing_channel_ids - channel_ids
        if unused_channel_ids:
            session.execute(
                delete(db.Channel)
                .where(db.Channel.id.in_(unused_channel_ids))
            )
            # db.Videos must be deleted explicitly because we are deleting in bulk
            # using Core instead of using the cascade properties of ORM
            session.execute(
                delete(db.Video)
                .where(db.Video.channel_id.in_(unused_channel_ids))
            )
        new_channel_ids = channel_ids - existing_channel_ids
        if new_channel_ids:
            values = [
                dict(id=channel_id)
                for channel_id in new_channel_ids
            ]
            session.execute(insert(db.Channel), values)


class Feed(TypedDict):
    title: str


class Entry(TypedDict):
    yt_videoid: str
    title: str
    published_parsed: struct_time


class ParsedFeed(TypedDict):
    feed: Feed
    entries: list[Entry]


def extract_channel_id(feed: str) -> str:
    match = channel_id_regex.fullmatch(feed)
    if match is None:
        raise ValueError("RSS feed doesn't match Youtube's RSS feed format")
    else:
        return match.group(1)


@dataclass
class Video:
    video: InitVar[db.Video]
    id: str = field(init=False)
    publication_dt: datetime = field(init=False)
    title: str = field(init=False)
    channel_id: str = field(init=False)
    channel_title: str = field(init=False)

    def __post_init__(self, video: db.Video) -> None:
        self.path = get_video_path(video.id)
        self.thumbnail_path = get_thumbnail_path(video.id)
        self.id = video.id
        self.publication_dt = video.publication_dt
        self.title = video.title
        self.channel_id = video.channel.id
        self.channel_title = video.channel.title or "Missing channel title"

    def download(self, **kwargs: Any) -> None:
        download_video_with_notification(self.id, **kwargs)

    @property
    def downloaded(self) -> bool:
        return Path(self.path).is_file()

    @property
    def downloading(self) -> bool | None:
        with db.Session() as session:
            return session.scalar(
                select(db.Video.downloading)
                .filter_by(id=id)
            )

    @property
    def thumbnail_downloaded(self) -> bool:
        return Path(self.thumbnail_path).is_file()

    # def download_thumbnail(self) -> None:
    #     if not self.thumbnail_downloaded:
    #         download_thumbnail(self.id, str(self.thumbnail_path))

    @property
    def watched(self) -> bool | None:
        with db.Session() as session:
            return session.scalar(
                select(db.Video.watched)
                .filter_by(id=id)
            )

    @watched.setter
    def watched(self, value: bool) -> None:
        with db.Session.begin() as session:
            session.execute(
                update(db.Video)
                .filter_by(id=self.id)
                .values(watched=value)
            )
        self.delete_assets()

    def delete_assets(self) -> None:
        delete_video_assets(self.id)

    def delete(self) -> None:
        delete_video(self.id)


def get_videos() -> Iterable[Video]:
    cutoff_dt = datetime.now() - config.no_older_than
    with db.Session() as session:
        videos = session.scalars(
            select(db.Video)
            .where(db.Video.publication_dt > cutoff_dt)
            .order_by(db.Video.publication_dt.desc())
            .filter_by(watched=False)
        )
        return tuple(map(Video, videos))


def create_video(id: str) -> Video:
    with db.Session() as session:
        return Video(session.get_one(db.Video, id))


def make_video_row(entry: Entry, channel_id: str) -> db.Video:
    timestamp = mktime(entry["published_parsed"])
    return db.Video(
        id=entry["yt_videoid"],
        channel_id=channel_id,
        title=entry["title"],
        publication_dt=datetime.fromtimestamp(timestamp),
    )


async def upload_feed_data(channel_id: str, parsed_feed: ParsedFeed) -> None:
    async with db.AsyncSession.begin() as sa_session:
        channel = await sa_session.get_one(db.Channel, channel_id)
        channel.title = parsed_feed['feed']['title']
        channel.last_updated = datetime.now()
        sa_session.add(channel)
        query = select(db.Video.id).filter_by(channel_id=channel_id)
        existing_video_ids = set(await sa_session.scalars(query))
        sa_session.add_all(
            make_video_row(entry, channel_id)
            for entry in parsed_feed['entries']
            if entry["yt_videoid"] not in existing_video_ids
        )


async def fetch_feed(
    http_session: aiohttp.ClientSession,
    channel_id: str
) -> None:
    feed_url = FEED_PREFIX + channel_id
    async with http_session.get(feed_url) as resp:
        if resp.status == 200:
            text = await resp.text()
            parsed_feed = feedparser.parse(text)
            await upload_feed_data(channel_id, parsed_feed)


async def download_thumbnail(
    http_session: ClientSession,
    video_id: str,
    callback: Optional[Callable[[str], None]],
) -> None:
    thumbnail_path = get_thumbnail_path(video_id)
    if not thumbnail_path.is_file():
        url = f"http://img.youtube.com/vi/{video_id}/mqdefault.jpg"
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(url) as resp:
                if resp.status == 200:
                    async with aiofiles.open(thumbnail_path, mode='wb') as f:
                        await f.write(await resp.read())
    if callback is not None:
        await asyncio.to_thread(callback, video_id)


async def fetch_feeds(
    callback: Optional[Callable[[str], None]] = None,
) -> None:
    with db.Session() as session:
        channel_ids = set(session.scalars(select(db.Channel.id)))
    async with aiohttp.ClientSession() as http_session:
        async with asyncio.TaskGroup() as tg:
            for channel_id in channel_ids:
                tg.create_task(fetch_feed(http_session, channel_id))
        with db.Session() as session:
            cutoff_dt = datetime.now() - config.no_older_than
            video_ids = set(session.scalars(
                select(db.Video.id)
                .where(db.Video.publication_dt > cutoff_dt)
            ))
        async with asyncio.TaskGroup() as tg:
            for video_id in video_ids:
                cr = download_thumbnail(http_session, video_id, callback)
                tg.create_task(cr)


def main() -> None:
    update_channels(config.channel_ids)
    asyncio.run(fetch_feeds())


class NewVideoEvent(Observable):
    def run(self) -> None:
        update_channels(config.channel_ids)
        def new_video_callback(video_id: str) -> None:
            self.notify_observers(video_id)
        asyncio.run(fetch_feeds(new_video_callback))


def query_video_ids(**kwargs: Any) -> Sequence[str]:
    cutoff_dt = datetime.now() - config.no_older_than
    with db.Session() as session:
        query_result = session.scalars(
            select(db.Video.id)
            .order_by(db.Video.publication_dt.desc())
            .where(db.Video.publication_dt > cutoff_dt)
            .filter_by(**kwargs)
        )
        return tuple(query_result)


def clean_assets() -> None:
    """Delete videos and thumbnails from videos that either don't exist in the database or have been watched"""
    video_ids = tuple(query_video_ids(watched=False))
    for video_path in config.video_dir.iterdir():
        if video_path.suffix != VIDEO_FORMAT:
            video_path.unlink()
        if video_path.stem not in video_ids:
            video_path.unlink()
    for thumbnail_path in config.thumbnail_dir.iterdir():
        if thumbnail_path.suffix != THUMBNAIL_FORMAT:
            thumbnail_path.unlink()
        if thumbnail_path.stem not in video_ids:
            thumbnail_path.unlink()


def update_fields(id: str, **kwargs: Any) -> None:
    with db.Session.begin() as session:
        session.execute(
            update(db.Video)
            .filter_by(id=id)
            .values(**kwargs)
        )


def create_notification(id: str) -> Notify.Notification:
    Notify.init()
    with db.Session() as session:
        title = session.scalar(select(db.Video.title).filter_by(id=id))
    with db.Session() as session:
        channel_title = session.scalar(
            select(db.Channel.title)
            .join(db.Video)
            .filter_by(id=id)
        )
    if channel_title is None:
        raise ValueError(f"db.Video with id {id} does not exist in the database")
    thumbnail_path = str(get_thumbnail_path(id))
    notification = Notify.Notification.new(channel_title, title, thumbnail_path)
    notification.set_timeout(Notify.EXPIRES_NEVER)
    notification.set_app_name("yt-player")
    tag = GLib.Variant.new_string(id)
    notification.set_hint("x-dunst-stack-tag", tag)
    return notification


def download_video_with_notification(
    id: str,
    with_notification: bool,
    **ytdlp_kwargs: Any
) -> None:
    update_fields(id, downloading=True)
    notification = create_notification(id) if with_notification else None
    video_path = str(get_video_path(id))
    ytdlp_kwargs["merge_output_format"] = VIDEO_FORMAT
    ytdlp_kwargs["noprogress"] = VIDEO_FORMAT

    download_video(
        url=id,
        path=video_path,
        notification=notification,
        **ytdlp_kwargs,
    )
    update_fields(id, downloading=False)


def delete_video_assets(id: str) -> None:
    video_path = get_video_path(id)
    Path(video_path).unlink(missing_ok=True)
    thumbnail_path = get_thumbnail_path(id)
    Path(thumbnail_path).unlink(missing_ok=True)

def delete_video(id: str) -> None:
    delete_video_assets(id)
    with db.Session.begin() as session:
        with session.begin():
            session.execute(
                delete(db.Video)
                .filter_by(id=id)
            )

