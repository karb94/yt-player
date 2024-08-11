from pathlib import Path
from collections.abc import Collection, Generator

import pytest
from sqlalchemy import create_engine, Engine
from yrp.backend import Backend
from yrp.db import Base


@pytest.fixture
def engine() -> Generator[Engine, None, None]:
    engine = create_engine("sqlite://")
    yield engine
    engine.dispose()


@pytest.fixture
def engine_with_tables(engine: Engine) -> Engine:
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def create_tables(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    return


# @pytest.fixture
# def real_channel_ids():
#     return ("UCXuqSBlHAE6Xw-yeJA0Tunw", "UCBJycsmduvYEL83R_U4JriQ")


@pytest.fixture
def thumbnail_dir(tmp_path: Path) -> str:
    thumbnail_dir_path = tmp_path / "thumbnail"
    return str(thumbnail_dir_path.absolute())


@pytest.fixture
def video_dir(tmp_path: Path) -> str:
    video_dir_path = tmp_path / "video"
    return str(video_dir_path.absolute())


@pytest.fixture
def backend(
    engine: Engine,
    thumbnail_dir: str,
    video_dir: str,
) -> Backend:
    return Backend(
        engine=engine,
        thumbnail_dir=thumbnail_dir,
        video_dir=video_dir,
    )
