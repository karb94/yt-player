from sqlalchemy import create_engine
from ui import MyApp
import sys
from backend import Backend


THUMBNAIL_DIR = "thumbnails"
VIDEO_DIR = "videos"

engine = create_engine('sqlite:///test.db')
backend = Backend(engine=engine, thumbnail_dir=THUMBNAIL_DIR, video_dir=VIDEO_DIR)
app = MyApp(backend=backend, application_id="com.github.yt-player")
app.run(sys.argv)
