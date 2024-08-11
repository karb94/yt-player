from datetime import datetime
from pytest_bdd.parsers import parse
from pytest_bdd import parsers
from collections.abc import Collection
from pytest_bdd import scenarios, scenario, given, when, then
from sqlalchemy.orm import Session
from yrp.backend import Backend
from sqlalchemy import inspect
from yrp.db import VideoTable, ChannelTable
from pathlib import Path
from sqlalchemy import Engine, select


scenarios("../features/update_channels.feature")

@given("no channels in the channel table")
def no_channels_in_table() -> None:
    pass


@given(
    parse("channel {channel_id} is in the channel table"),
    target_fixture='engine',
)
def database_has_channel(
    engine_with_tables: Engine,
    channel_id: str
) -> Engine:
    with Session(engine_with_tables) as session:
        channel = ChannelTable(id=channel_id)
        session.add(channel)
        session.commit()
    return engine_with_tables

@given(
    parse(
        "video {video_id} from channel {channel_id} "
        "is in the video table"
    ),
    target_fixture='engine',
)
def backend_with_video_from_channel(
    engine_with_tables: Engine,
    channel_id: str,
    video_id: str,
) -> Engine:
    with Session(engine_with_tables) as session:
        video = VideoTable(
            id=video_id,
            title=video_id,
            publication_dt=datetime(year=2000, month=1, day=1),
            channel_id=channel_id,
        )
        session.add(video)
        session.commit()
    return engine_with_tables


@when(
    parse("the channels are updated with channel {channel_id}"),
    target_fixture='backend',
)
def update_channels(backend: Backend, channel_id: str) -> Backend:
    backend.update_channels({channel_id})
    return backend


@then(parse( "the channel {channel} should not be in the channel table"))
def channel_not_in_table(backend: Backend, channel: str) -> None:
    with Session(backend.engine) as session:
        query_result = session.scalars(
            select(ChannelTable)
            .filter_by(id=channel)
        )
        assert query_result.one_or_none() is None


@then(parse("the video {video_id} should not be in the video table"))
def video_not_in_table(backend: Backend, video_id: str) -> None:
    with Session(backend.engine) as session:
        query_result = session.scalars(
            select(VideoTable)
            .filter_by(id=video_id)
        )
        assert query_result.one_or_none() is None


@then(parse( "the channel {channel_id} should be in the channel table"))
def channel_in_table(backend: Backend, channel_id: str) -> None:
    with Session(backend.engine) as session:
        query_result = session.scalars(
            select(ChannelTable)
            .filter_by(id=channel_id)
        )
        assert query_result.one_or_none() is not None

@then(parse("the video {video_id} should be in the video table"))
def video_in_table(backend: Backend, video_id: str) -> None:
    with Session(backend.engine) as session:
        query_result = session.scalars(
            select(VideoTable)
            .filter_by(id=video_id)
        )
        assert query_result.one_or_none() is not None
