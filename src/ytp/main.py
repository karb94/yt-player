from sqlalchemy import create_engine
from ui import MyApp
import sys
from backend import Backend
from xdg.BaseDirectory import save_data_path, save_config_path
from pathlib import Path
import tomllib
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    data_path = Path(save_data_path("yrp"))
    thumbnail_dir = str(data_path / "thumbnails")
    video_dir = str(data_path / "videos")
    config_path = Path(save_config_path("yrp"))
    config_file = config_path / "yrp.toml"
    with config_file.open("rb") as file:
        config = tomllib.load(file)
        channel_ids = config["channels"]
        channel_id_regex = re.compile(r"[\w-]{24}")
        for channel_id in config["channels"]:
            if channel_id_regex.fullmatch(channel_id) is None:
                raise ValueError(f"'{channel_id}' is not a valid channel ID")

    engine = create_engine('sqlite:///test.db')
    backend = Backend(
        engine=engine,
        thumbnail_dir=thumbnail_dir,
        video_dir=video_dir,
        channel_ids=channel_ids,
    )
    logger.info('Attaching backend to the app')
    app = MyApp(backend=backend, application_id="com.github.yrp")
    logger.info('Running the app')
    app.run(sys.argv)
