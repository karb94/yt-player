from datetime import timedelta
from xdg_base_dirs import (
    xdg_config_home,
    xdg_data_home,
    xdg_cache_home,
)
import tomllib
import re
import logging

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

if config_file.is_file():
    with config_file.open("rb") as file:
        config = tomllib.load(file)
        channel_ids = set(config["channels"])
        channel_id_regex = re.compile(r"[\w-]{24}")
        for channel_id in config["channels"]:
            if channel_id_regex.fullmatch(channel_id) is None:
                raise ValueError(f"'{channel_id}' is not a valid channel ID")
else:
    channel_ids = set()

no_older_than = timedelta(days=1)
