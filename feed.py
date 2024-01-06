from datetime import datetime
import re

import feedparser
import pandas as pd
from sqlalchemy import insert, select, update
from sqlalchemy.engine.base import Engine

from db import channel_table

VIDEO_ATTRIBUTES = [
    "yt_videoid",
    "title",
    "link",
    "media_thumbnail",
    "published",
]
FEED_PREFIX = "https://www.youtube.com/feeds/videos.xml?channel_id="
channel_id_regex = re.compile(re.escape(FEED_PREFIX) + r"([\w-]{24})")


def extract_channel_id(feed: str) -> str:
    match = channel_id_regex.fullmatch(feed)
    if match is None:
        raise ValueError("RSS feed doesn't match Youtube's RSS feed format")
    else:
        return match.group(1)


def add_new_channels(engine: Engine, feeds: list[str]):
    channel_ids = set(map(extract_channel_id, feeds))
    with engine.begin() as conn:
        query_result = conn.execute(select(channel_table.c.id))
        db_channel_ids = set(query_result.scalars().all())
        missing_channel_ids = channel_ids - db_channel_ids
        values = [dict(id=channel_id) for channel_id in missing_channel_ids]
        conn.execute(insert(channel_table), values)


def download_feeds(engine: Engine):
    with engine.begin() as conn:
        query_result = conn.execute(select(channel_table.c.id))
        channel_ids = set(query_result.scalars().all())
    feeds = [FEED_PREFIX + channel_id for channel_id in  channel_ids]
    return map(feedparser.parse, feeds)


def add_new_videos(engine: Engine, parsed_feed):
    channel_id = parsed_feed.feed.yt_channelid
    with engine.begin() as conn:
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
    video_df.to_sql("video", engine, if_exists="append")


def update_channel(engine: Engine, parsed_feed):
    channel_id = parsed_feed.feed.yt_channelid
    channel_title = parsed_feed.feed.yt_channelid
    with engine.begin() as conn:
        conn.execute(
            update(channel_table)
            .where(channel_table.c.id == channel_id)
            .values(title=channel_title, last_updated=datetime.now())
        )
    add_new_videos(engine, parsed_feed)
