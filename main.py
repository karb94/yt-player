# from IPython.core.debugger import set_trace
from sqlalchemy import create_engine, select

from db import metadata, channel_table, video_table
from feed import add_new_channels, download_feeds, update_channel
from download import download_thumbnails, validate_thumbnail_paths
from ui import buildCards, MyWindow

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


THUMBNAILS_DIR = "thumbnails"

feeds = [
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCXuqSBlHAE6Xw-yeJA0Tunw",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCBJycsmduvYEL83R_U4JriQ",
]


engine = create_engine('sqlite:///test.db')
metadata.drop_all(engine)
metadata.create_all(engine)

add_new_channels(engine, feeds)

for parsed_feed in download_feeds(engine):
    if parsed_feed["status"] != 200:
        raise ConnectionError(f"feedparser exited with status {parsed_feed['status']}")
    update_channel(engine, parsed_feed)

validate_thumbnail_paths(engine, dir=THUMBNAILS_DIR)
download_thumbnails(engine, dir=THUMBNAILS_DIR)

with engine.begin() as conn:
    query_result = conn.execute(
        select(video_table)
        .where(video_table.c.thumbnail_path.is_not(None))
    )
    img_paths = [row.thumbnail_path for row in query_result]

cards = buildCards(img_paths)
win = MyWindow(cards)
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
