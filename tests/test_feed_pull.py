import asyncio
from datetime import datetime
from yrp.db import Session, AsyncSession, Channel, Video, Base
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine
from yrp.backend import upload_feed_data, Feed, Entry, ParsedFeed
import pytest


@pytest.mark.asyncio
async def test_feed_upload(async_engine: AsyncEngine, async_db: None) -> None:
    channel_id = 'A'
    video_id = 'A1'
    feed = Feed(title=channel_id)
    publication_dt = datetime(year=2000, month=1, day=1)
    entry = Entry(
        yt_videoid=video_id,
        title=video_id,
        published_parsed=publication_dt.timetuple(),
    )
    parsed_feed = ParsedFeed(
        feed=feed,
        entries=[entry]
    )
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession() as session:
        channel = Channel(id=channel_id)
        session.add(channel)
        await session.commit()

    await upload_feed_data(channel_id=channel_id, parsed_feed=parsed_feed)

    async with AsyncSession() as session:
        channel = await session.get_one(Channel, channel_id)
        await session.refresh(channel, ["title", "videos"])
        assert channel.title == parsed_feed["feed"]["title"]
        assert len(channel.videos) == 1
        video = channel.videos[0]
        assert video.title == parsed_feed["entries"][0]["title"]
        assert video.id == parsed_feed["entries"][0]["yt_videoid"]
        assert video.publication_dt == publication_dt


@pytest.mark.asyncio
async def test_feed_upload_with_existing_video(
    async_engine: AsyncEngine,
    async_db: None
) -> None:
    channel_id = 'A'
    video_id = 'A1'
    feed = Feed(title=channel_id)
    publication_dt = datetime(year=2000, month=1, day=1)
    entry = Entry(
        yt_videoid=video_id,
        title=video_id,
        published_parsed=publication_dt.timetuple(),
    )
    parsed_feed = ParsedFeed(
        feed=feed,
        entries=[entry]
    )
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession() as session:
        channel = Channel(id=channel_id, )
        existing_video = Video(
            id='A2',
            title='A2',
            publication_dt=publication_dt,
            channel_id=channel_id,
        )
        channel.videos = [existing_video]
        session.add(channel)
        await session.commit()

    await upload_feed_data(channel_id=channel_id, parsed_feed=parsed_feed)

    async with AsyncSession() as session:
        channel = await session.get_one(Channel, channel_id)
        await session.refresh(channel, ["title", "videos"])
        assert channel.title == parsed_feed["feed"]["title"]
        assert len(channel.videos) == 2
        existing_video = channel.videos[0]
        assert existing_video.title == 'A2'
        assert existing_video.id == 'A2'
        assert existing_video.publication_dt == publication_dt
        new_video = channel.videos[1]
        assert new_video.title == parsed_feed["entries"][0]["title"]
        assert new_video.id == parsed_feed["entries"][0]["yt_videoid"]
        assert new_video.publication_dt == publication_dt

