from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, MetaData, String, Table, Boolean
from typing import List
from typing import Optional
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

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
    Column("downloading", Boolean, default=False),
    Column("read", Boolean, default=False),
)



class Base(DeclarativeBase):
    pass

class ChannelTable(Base):
    __tablename__ = "channel"
    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    title: Mapped[str] = mapped_column(String)
    last_updated: Mapped[Optional[str]]
    videos: Mapped[List["VideoTable"]] = relationship(back_populates="channel")

class VideoTable(Base):
    __tablename__ = "video"
    id: Mapped[str] = mapped_column(String(11), primary_key=True)
    title: Mapped[str]
    publication_dt: Mapped[datetime]
    downloading: Mapped[bool] = mapped_column(default=False)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channel.id"))
    channel: Mapped["ChannelTable"] = relationship(back_populates="videos")

