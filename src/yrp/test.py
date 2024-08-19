from sqlalchemy.orm import selectinload
from backend import *
from db import *
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import create_engine

cis = [
    "UCXuqSBlHAE6Xw-yeJA0Tunw",
    "UCBJycsmduvYEL83R_U4JriQ",
]

engine = create_engine('sqlite:///test.db')
Session.configure(bind=engine)
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)

async_engine = create_async_engine('sqlite+aiosqlite:///test.db')
AsyncSession.configure(bind=async_engine)


def update_channels(channel_ids: Set[str]) -> None:
    with Session() as session:
        query_result = session.scalars(select(db.Channel.id))
        existing_channel_ids = set(query_result.all())
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
        session.commit()


async def async_main():
    await fetch_feeds(cis)

async def fetch_feed(
    http_session: aiohttp.ClientSession,
    channel_id: str
) -> None:
    feed_url = FEED_PREFIX + channel_id
    async with http_session.get(feed_url) as resp:
        if resp.status == 200:
            text = await resp.text()
            parsed_feed = feedparser.parse(text)
            async with AsyncSession() as sa_session:
                query_result = await sa_session.scalars(select(db.Video.id))
                existing_video_ids = frozenset(query_result)
                videos = [
                    parse_entry(entry)
                    for entry in parsed_feed['entries']
                    if entry["yt_videoid"] not in existing_video_ids
                ]
                channel = await sa_session.get_one(
                    db.Channel,
                    channel_id,
                )
                channel.title = parsed_feed['feed']['title']
                await sa_session.refresh(channel, ["videos"])
                channel.videos.extend(videos)
                sa_session.add(channel)
                await sa_session.commit()


async def fetch_feeds(channel_ids: Iterable[str]) -> None:
    async with aiohttp.ClientSession() as http_session:
        async with asyncio.TaskGroup() as tg:
            for channel_id in channel_ids:
                tg.create_task(fetch_feed(http_session, channel_id))

update_channels(set(cis))
asyncio.run(async_main())

