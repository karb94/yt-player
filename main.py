from sqlalchemy import create_engine
from ui import MyApp
import sys
from backend import Backend
from xdg.BaseDirectory import save_data_path, save_config_path
from pathlib import Path



data_path = Path(save_data_path("yrp"))
thumbnail_dir = str(data_path / "thumbnails")
video_dir = str(data_path / "videos")
config_path = Path(save_config_path("yrp"))
config_file = config_path /  "yrp.toml"
with config_file.open() as file:
    channel_ids = []
    for n, line in enumerate(file.read().splitlines(), start=1):
        print(line)
        print(line.strip())
        print(len(line.strip()))
        print(len(line.strip(" ")))
        if len(line.strip()) != len(line):
            raise ValueError(
                f"Line {n} in {config_file} "
                f"has leading and/or trailing spaces:\n{line}"
            )
        if len(line) != 24:
            raise ValueError(
                f"Line {n} in {config_file} "
                f"has {len(line)} characters when 24 are required:\n{line}"
            )

        channel_ids.append(line)

engine = create_engine('sqlite:///test.db')
backend = Backend(
    engine=engine,
    thumbnail_dir=thumbnail_dir,
    video_dir=video_dir,
    channel_ids=channel_ids,
)
app = MyApp(backend=backend, application_id="com.github.yrp")
app.run(sys.argv)
