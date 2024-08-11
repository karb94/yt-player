from datetime import datetime
# from pytest_bdd.parsers import parse
from pytest_bdd import parsers
from collections.abc import Collection
from pytest_bdd import scenarios, scenario, given, when, then
from sqlalchemy.orm import Session
from yrp.backend import Backend
from sqlalchemy import inspect
from yrp.db import VideoTable, ChannelTable
from pathlib import Path
from sqlalchemy import Engine, select


scenarios("../features/backend_init.feature")


@when(
    "the backend is initialized:\n"
    "- with empty database\n"
    "- with empty thumbnail and video directories\n"
    "- without channels"
)
def init_backend_without_channels(backend: Backend) -> None:
    pass


@then("the channel and video tables should be created")
def db_contains_tables(
    backend: Backend,
) -> None:
    assert inspect(backend.engine).has_table(ChannelTable.__tablename__)
    assert inspect(backend.engine).has_table(VideoTable.__tablename__)


@then("the thumbnail and video directories should be created")
def thumbnail_and_video_dirs_exist(thumbnail_dir: str, video_dir: str) -> None:
    Path(thumbnail_dir).is_dir()
    Path(video_dir).is_dir()


@then("the thumbnail and video directories should be stored in the Backend object")
def test_thumbnail_and_video_attributes(
    backend: Backend,
    thumbnail_dir: str,
    video_dir: str
) -> None:
    assert backend.thumbnail_dir == thumbnail_dir
    assert backend.video_dir == video_dir

