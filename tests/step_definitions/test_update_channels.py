from datetime import datetime
from pytest_bdd.parsers import parse
from pytest_bdd import scenarios, given, when, then
from yrp.backend import update_channels
from yrp.db import Session, Channel, Video
from sqlalchemy import select


scenarios("../features/update_channels.feature")


@given("no channels in the channel table")
def no_channels_in_table() -> None:
    pass


@given(
    parse("channel {channel_id} is in the channel table"),
    target_fixture="engine",
)
def database_has_channel(channel_id: str) -> None:
    with Session() as session:
        channel = Channel(id=channel_id)
        session.add(channel)
        session.commit()


@given(
    parse("video {video_id} from channel {channel_id} is in the video table")
)
def db_with_video_from_channel(channel_id: str, video_id: str) -> None:
    with Session() as session:
        video = Video(
            id=video_id,
            title=video_id,
            publication_dt=datetime(year=2000, month=1, day=1),
            channel_id=channel_id,
        )
        session.add(video)
        session.commit()


@when(parse("the channels are updated with channel {channel_id}"))
def run_update_channels(channel_id: str) -> None:
    update_channels({channel_id})


@then(parse("the channel {channel_id} should be in the channel table"))
def channel_in_table(channel_id: str) -> None:
    with Session() as session:
        query_result = session.scalars(
            select(Channel).filter_by(id=channel_id)
        )
        assert query_result.one_or_none() is not None


@then(parse("the video {video_id} should be in the video table"))
def video_in_table(video_id: str) -> None:
    with Session() as session:
        query_result = session.scalars(select(Video).filter_by(id=video_id))
        assert query_result.one_or_none() is not None


@then(parse("the channel {channel} should not be in the channel table"))
def channel_not_in_table(channel: str) -> None:
    with Session() as session:
        query_result = session.scalars(select(Channel).filter_by(id=channel))
        assert query_result.one_or_none() is None


@then(parse("the video {video_id} should not be in the video table"))
def video_not_in_table(video_id: str) -> None:
    with Session() as session:
        query_result = session.scalars(select(Video).filter_by(id=video_id))
        assert query_result.one_or_none() is None
