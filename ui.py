from datetime import datetime
from subprocess import Popen
from threading import Thread
from dateutil.relativedelta import relativedelta
from typing import Any

from download import parse_progress
from backend import Backend, Video
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version("Notify", "0.7")
from gi.repository import Gtk, Gdk, Adw, GLib


css_provider = Gtk.CssProvider()
css_provider.load_from_path('style.css')
display = Gdk.Display.get_default()
if display is None:
    raise TypeError
Gtk.StyleContext.add_provider_for_display(display, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

def get_time_ago(date_time: datetime) -> str:
    units = ("year", "month", "day", "hour", "minute")
    time_delta = relativedelta(datetime.now(), date_time)
    for unit in units:
        value = getattr(time_delta, unit+"s")
        if value == 0:
            continue
        s = "s" if value > 1 else ""
        return f"{value} {unit}{s} ago"
    return "1 min ago"


class VideoCard(Gtk.ListBoxRow):
    def __init__(self, video: Video, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.video = video

        grid = Gtk.Grid()
        grid.props.width_request = 300
        self.set_child(grid)
        if not self.video.thumbnail_downloaded:
            self.video.download_thumbnail()
        img = Gtk.Picture.new_for_filename(video.thumbnail_path)
        img.props.halign = Gtk.Align.START
        img.props.can_shrink = False
        grid.attach(child=img, column=1, row=1, width=1, height=4) 
        title = video.title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        title_label = Gtk.Label(
            label=rf'<span weight="bold" size="x-large">{title}</span>',
            use_markup=True,
            halign=Gtk.Align.START,
            vexpand=True,
            margin_start=10,
        )
        grid.attach(child=title_label, column=2, row=1, width=1, height=1) 
        channel_label = Gtk.Label(
            label=video.channel_title,
            halign=Gtk.Align.START,
            vexpand=True,
            margin_start=10,
        )
        grid.attach(child=channel_label, column=2, row=2, width=1, height=1) 
        time_ago = get_time_ago(video.publication_dt)
        publication_label = Gtk.Label(
            label=time_ago,
            halign=Gtk.Align.START,
            vexpand=True,
            margin_start=10,
        )
        grid.attach(child=publication_label, column=2, row=3, width=1, height=1) 
        self.progress_bar = Gtk.ProgressBar(
            hexpand=True,
            show_text=True,
            fraction=1 if video.downloaded else 0,
            # margin_start=10,
            # margin_end=30,
        )
        self.progress_bar_label = self.progress_bar.get_first_child()
        if self.progress_bar_label is None:
            return
        self.progress_bar_label.props.halign = Gtk.Align.START
        self.progress_bar_label.props.margin_start = 10
        grid.attach(child=self.progress_bar, column=2, row=4, width=1, height=1) 


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, backend: Backend, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.backend = backend

        self.shortcut_hits = 0
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.label = Gtk.Label(label="")
        self.box.append(self.label)
        # self.box.append(self.scrolled_window)

        self.scrolled_window = Gtk.ScrolledWindow()
        self.set_child(self.scrolled_window)
        self.list_box = Gtk.ListBox()
        video_ids = self.backend.query_video_ids(watched=False)
        for video_id in video_ids:
            video = self.backend.create_video(video_id)
            self.list_box.append(VideoCard(video))
        # self.scrolled_window.set_child(self.list_box)
        self.box.append(self.list_box)
        self.scrolled_window.set_child(self.box)
        # self.button1 = Gtk.Button(label="Hello")
        # self.list_box.append(self.button1)

        evk = Gtk.EventControllerKey.new()
        evk.connect("key-pressed", self.key_press)
        self.add_controller(evk)

    def key_press(
        self,
        _event: Gdk.Event,
        keyval: int,
        _keycode: int,
        _state: Gdk.ModifierType,
    ) -> None:
        del _event, _keycode, _state
        match keyval:
            case Gdk.KEY_j:
                self.list_box.child_focus(Gtk.DirectionType.TAB_FORWARD)
            case Gdk.KEY_k:
                self.list_box.child_focus(Gtk.DirectionType.TAB_BACKWARD)
            case Gdk.KEY_d:
                video_card = self.list_box.get_focus_child()
                if video_card is None or not isinstance(video_card, VideoCard):
                    return
                if video_card.video.downloaded:
                    return
                if not isinstance(video_card, VideoCard):
                    return
                f = video_card.progress_bar.set_fraction

                def progress_hook(download: dict[str, Any]) -> None:
                    progress = parse_progress(download)
                    GLib.idle_add(f, progress)

                thread = Thread(
                    target=video_card.video.download,
                    kwargs=dict(with_notification=True, progress_hooks=[progress_hook])
                )
                thread.start()
            case Gdk.KEY_p:
                video_card = self.list_box.get_focus_child()
                if video_card is None or not isinstance(video_card, VideoCard):
                    return
                if not video_card.video.downloaded:
                    return
                cmd = (
                    "mpv",
                    "--keepaspect-window",
                    "--geometry=70%",
                    "--no-terminal",
                    "--cursor-autohide=no",
                    video_card.video.path,
                )
                Popen(cmd)
            case Gdk.KEY_w:
                video_card = self.list_box.get_focus_child()
                if video_card is None or not isinstance(video_card, VideoCard):
                    return
                self.list_box.child_focus(Gtk.DirectionType.TAB_FORWARD)
                video_card.video.watched = True
                video_card.set_visible(False)
            case Gdk.KEY_q:
                self.close()


class MyApp(Adw.Application):
    def __init__(self, backend: Backend, *args: Any, **kwargs: Any):
        self.backend = backend
        super().__init__(*args, **kwargs)
        self.connect('activate', self.on_activate)

    def on_activate(self, app: Adw.Application) -> None:
        self.win = MainWindow(backend=self.backend, application=app)
        self.win.present()

