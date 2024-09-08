from dataclasses import dataclass, field
from datetime import timedelta
from xdg_base_dirs import (
    xdg_config_home,
    xdg_data_home,
    xdg_cache_home,
)
import tomllib
import re
import logging
from pydantic import BaseModel, StringConstraints, Field, TypeAdapter
from typing import Pattern, TypedDict, NotRequired
from typing_extensions import Annotated

from yrp.backend import VideoEntry


logger = logging.getLogger(__name__)

APP_NAME = "yrp"

config_path = xdg_config_home() / APP_NAME
data_path = xdg_data_home() / APP_NAME
cache_path = xdg_cache_home() / APP_NAME

config_path.mkdir(parents=True, exist_ok=True)
data_path.mkdir(parents=True, exist_ok=True)
cache_path.mkdir(parents=True, exist_ok=True)

thumbnail_dir = cache_path / "thumbnails"
video_dir = cache_path / "videos"

thumbnail_dir.mkdir(parents=True, exist_ok=True)
video_dir.mkdir(parents=True, exist_ok=True)

config_file = config_path / f"{APP_NAME}.toml"
database_file = data_path / "yrp.db"

logger.info(f'{thumbnail_dir=}')
logger.info(f'{video_dir=}')
logger.info(f'{config_file=}')

channel_id_regex = re.compile(r"[\w-]{24}")


class ChannelEntry(TypedDict):
    id: str
    include: NotRequired[list[str] | str]
    exclude: NotRequired[list[str] | str]
    include_regex: NotRequired[list[str] | str]
    exclude_regex: NotRequired[list[str] | str]


class ChannelFilter(BaseModel):
    include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)
    include_regex: list[Pattern] = Field(default_factory=list)
    exclude_regex: list[Pattern] = Field(default_factory=list)

    def filter(self, video_entry: VideoEntry) -> bool:
        title = video_entry["title"]
        if self.exclude:
            if any(s in title for s in self.include):
                return False
        if self.exclude_regex:
            if any(pattern.match(title) for pattern in self.exclude_regex):
                return False

        if not self.include and not self.include_regex:
            return True
        if self.include:
            if any(s in title for s in self.include):
                return True
        if self.include_regex:
            if any(pattern.match(title) for pattern in self.include_regex):
                return True
        return False



channel_filters = {}
channel_ids = set()
if config_file.is_file():
    with config_file.open("rb") as file:
        config = tomllib.load(file)
        for channel_entry in config["channels"]:
            if isinstance(channel_entry, str):
                channel_id = channel_entry
                continue
            else:
                TypeAdapter(ChannelEntry).validate_python(channel_entry)
                channel_id = channel_entry.pop("id")
                if channel_entry:
                    channel_filter = ChannelFilter.model_validate(channel_entry)
                    channel_filters[channel_id] = channel_filter
            if channel_id_regex.fullmatch(channel_id) is None:
                raise ValueError( f"Channel ID '{channel_id}' is not valid")
            channel_ids.add(channel_id)

no_older_than = timedelta(days=1)
