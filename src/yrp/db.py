from datetime import datetime
from sqlalchemy import ForeignKey, String
from typing import List
from typing import Optional
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship


class Base(DeclarativeBase):
    pass

class ChannelTable(Base):
    __tablename__ = "channel"
    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    title: Mapped[Optional[str]] = mapped_column(String)
    last_updated: Mapped[Optional[str]]
    videos: Mapped[List["VideoTable"]] = relationship(
        back_populates="channel",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

class VideoTable(Base):
    __tablename__ = "video"
    id: Mapped[str] = mapped_column(String(11), primary_key=True)
    title: Mapped[str]
    publication_dt: Mapped[datetime]
    downloading: Mapped[bool] = mapped_column(default=False)
    watched: Mapped[bool] = mapped_column(default=False)
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("channel.id", ondelete="CASCADE", onupdate="CASCADE")
    )
    channel: Mapped["ChannelTable"] = relationship(back_populates="videos")

