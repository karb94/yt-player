from sqlalchemy import Column, DateTime, ForeignKey, MetaData, String, Table, Boolean

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
    Column("url", String),
    Column("publication_dt", DateTime),
    Column("path", String),
    Column("thumbnail_url", String),
    Column("thumbnail_path", String),
    Column("downloading", Boolean, default=False),
    Column("read", Boolean, default=False),
)
