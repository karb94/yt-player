import feedparser
import pandas as pd
from sqlalchemy import create_engine, insert
from db import metadata, channel_table

feeds = [
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCXuqSBlHAE6Xw-yeJA0Tunw"
]

video_attributes = [
    "yt_videoid",
    "title",
    "link",
    "media_thumbnail",
    "published",
]

def update_channels(engine, parsed_feed):
    channel_id = parsed_feed.feed.yt_channelid
    channel_title = parsed_feed.feed.yt_channelid
    stmt = insert(channel_table).values(id=channel_id, title=channel_title)
    with engine.begin() as conn:
        conn.execute(stmt)

def update_videos(engine, parsed_feed):
    if parsed_feed["status"] != 200:
        raise ConnectionError(f"feedparser exited with status {parsed_feed['status']}")
    video_df = pd.DataFrame(data=parsed_feed.entries, columns=video_attributes)
    video_df = (
        video_df
            .assign(
                published=pd.to_datetime(video_df["published"]),
                media_thumbnail=video_df["media_thumbnail"].map(lambda x: x[0]["url"]),
                channel_id=parsed_feed.feed.yt_channelid,
            )
            .rename(columns={
                "yt_videoid": "id",
                "link": "url",
                "media_thumbnail": "thumbnail_url",
                "published": "publication_dt",
            })
            .set_index("id")
            .sort_values("publication_dt")
    )
    video_df.to_sql("video", engine, if_exists='replace')

engine = create_engine('sqlite:///test.db', echo=True)
metadata.drop_all(engine)
metadata.create_all(engine)


for parsed_feed in map(feedparser.parse, feeds):
    update_videos(engine, parsed_feed)

