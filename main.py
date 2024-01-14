from sqlalchemy import Engine, create_engine, select
from ui import MyApp
import sys
from backend import Backend


THUMBNAIL_DIR = "thumbnails"
VIDEO_DIR = "videos"

# cards = buildCards(img_paths)
# win = MyWindow(cards)
# win.connect("destroy", Gtk.main_quit)
# win.show_all()
# Gtk.main()

engine = create_engine('sqlite:///test.db')
backend = Backend(engine=engine, thumbnail_dir=THUMBNAIL_DIR, video_dir=VIDEO_DIR)
app = MyApp(backend=backend, application_id="com.github.karb94.yt-player")
app.run(sys.argv)
