from sqlalchemy import Column, DateTime, ForeignKey, LargeBinary, MetaData, String, Table

metadata = MetaData()

channel_table = Table(
    "channel",
    metadata,
    Column("id", String, primary_key=True),
    Column("title", String),
    Column("last_updated", DateTime),
)
video_table = Table(
    "video",
    metadata,
    Column("id", String, primary_key=True),
    Column("channel_id", ForeignKey("channel.id")),
    Column("title", String()),
    Column("publication_dt", DateTime),
    Column("url", String),
    Column("video_path", String),
    Column("thumbnail_url", String),
    Column("thumbnail_path", String),
)
