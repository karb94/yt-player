from datetime import datetime
from sqlalchemy import ForeignKey, String
from typing import List, Optional
from sqlalchemy import ForeignKey, String, create_engine
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
)
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from yrp.config import database_file


class Base(DeclarativeBase):
    pass


def bind_engines(db_path: str) -> None:
    Session.configure(bind=create_engine(sync_db_url))
    AsyncSession.configure(bind=create_async_engine(async_db_url))
    Base.metadata.create_all(Session().get_bind())


class Channel(Base):
    __tablename__ = "channel"
    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    title: Mapped[Optional[str]] = mapped_column(String)
    last_updated: Mapped[Optional[datetime]]
    videos: Mapped[List["Video"]] = relationship(
        back_populates="channel",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Video(Base):
    __tablename__ = "video"
    id: Mapped[str] = mapped_column(String(11), primary_key=True)
    title: Mapped[str]
    publication_dt: Mapped[datetime]
    downloading: Mapped[bool] = mapped_column(default=False)
    watched: Mapped[bool] = mapped_column(default=False)
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("channel.id", ondelete="CASCADE", onupdate="CASCADE")
    )
    channel: Mapped["Channel"] = relationship(back_populates="videos")


# Set up syncronous session
sync_db_url = f'sqlite:///{database_file}'
engine = create_engine(sync_db_url)
Session = sessionmaker(bind=engine)

# Set up asyncronous session
async_db_url = f'sqlite+aiosqlite:///{database_file}'
async_engine = create_async_engine(async_db_url)
AsyncSession = async_sessionmaker(bind=async_engine)

# Create tables if missing
Base.metadata.create_all(engine)
