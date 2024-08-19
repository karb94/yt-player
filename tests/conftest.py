from pathlib import Path
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from yrp.backend import Backend
from yrp.db import Base, Session, AsyncSession


get_db_url = "sqlite+{driver}:///file:test_db?mode=memory&uri=true".format


@pytest.fixture(autouse=True)
def db() -> None:
    url = get_db_url(driver='pysqlite')
    Session.configure(bind=create_engine(url))
    Base.metadata.create_all(Session().get_bind())


@pytest.fixture()
def async_engine() -> AsyncEngine:
    url = get_db_url(driver='aiosqlite')
    return create_async_engine(url)

@pytest.fixture()
def async_db(async_engine: AsyncEngine) -> None:
    AsyncSession.configure(bind=async_engine)


@pytest.fixture
def tmp_cache_dir(tmp_path: Path) -> Path:
    os.environ['XDG_CACHE'] = str(tmp_path)
    return tmp_path

@pytest.fixture
def thumbnail_dir(tmp_cache_dir: Path) -> Path:
    thumbnail_dir_path = tmp_cache_dir / "thumbnail"
    return thumbnail_dir_path


@pytest.fixture
def video_dir(tmp_cache_dir: Path) -> Path:
    video_dir_path = tmp_cache_dir / "video"
    return video_dir_path


@pytest.fixture
def backend() -> Backend:
    return Backend()
