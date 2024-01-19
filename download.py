from pathlib import Path
from yt_dlp import YoutubeDL
from urllib.request import urlretrieve
from pprint import pp

get_thumbnail_url = "http://img.youtube.com/vi/{video_id}/mqdefault.jpg".format

FORMATS_RANKING = (
    "bestvideo[width=2560][vcodec=vp09.00.50.08][ext=mp4]+bestaudio",
    "bestvideo[width=2560][vcodec=vp9][ext=mp4]+bestaudio",
    "bestvideo[width=2560][vcodec=vp09.00.50.08]+bestaudio",
    "bestvideo[width=2560]+bestaudio",
    "bestvideo[width<=2560]+bestaudio",
    "best",
)

default_options = {
    "format": "/".join(FORMATS_RANKING),
    "merge_output_format": "mkv",
    "noprogress": True,
}

def download_thumbnail(video_id: str, dir: str) -> str:
    thumbnail_dir = Path(dir)
    thumbnail_dir.mkdir(parents=True, exist_ok=True)
    url = get_thumbnail_url(video_id=video_id)
    ext = Path(url).suffix
    filename = video_id + ext
    thumbnail_path = thumbnail_dir / filename
    urlretrieve(url, thumbnail_path)
    return str(thumbnail_path)


def parse_progress(download: dict):
    # print(progress["status"])
    if "info_dict" in download:
        del download["info_dict"]
    # if progress["status"] == "
    if "fragment_count" in download and "fragment_index" in download:
        if download["fragment_index"] > download["fragment_count"]+1:
            pp(download)
            raise KeyError(f"No keys to calculate errors. Keys available {pp(list(download))}")
        else:
            progress = download["fragment_index"] / (download["fragment_count"]+1)
    elif all(k in download for k in ("downloaded_bytes", "total_bytes")):
        progress = download["downloaded_bytes"] / download["total_bytes"]
    elif all(k in download for k in ("downloaded_bytes", "total_bytes_estimate")):
        progress = download["downloaded_bytes"] / download["total_bytesestimate"]
    elif "fragment_count" in download and "fragment_index" in download:
        if download["fragment_index"] > download["fragment_count"]:
            pp(download)
            raise KeyError(f"No keys to calculate errors. Keys available {pp(list(download))}")
        else:
            progress = download["fragment_index"] / (download["fragment_count"]+1)
    else:
        return None
    # progress = download["downloaded_bytes"] / download["total_bytes"]
    # eta = download["eta"]
    # speed = download["speed"]
    # elapsed = download["elapsed"]
    return progress


def download_video(url: str, dir: str, filename: str, with_notification: bool, **ytdlp_kwargs):

    thumbnail_path = self.get_field(id=id, field="thumbnail_path")
    Notify.init()
    title = self.get_field(id=id, field="title")
    summary = f"Preparing download"
    notification = Notify.Notification.new(summary, title, thumbnail_path)
    notification.set_timeout(Notify.EXPIRES_NEVER)
    notification.set_app_name("yt-player")
    notification.show()

    def notification_hook(d):
        progress_frac = parse_progress(d)
        if isinstance(progress_frac, float):
            value = GLib.Variant.new_uint32(int(progress_frac*100))
            notification.set_hint("value", value)
            tag = GLib.Variant.new_string(id)
            notification.set_hint("x-dunst-stack-tag", tag)
            # fgcolor = GLib.Variant.new_string("#ff4444")
            # notification.set_hint("fgcolor", fgcolor)
            notification.show()


    video_path = f"{dir}/{id}.{ext}"
    %(id)s].%(ext)s
    ytdlp_kwargs["outtmpl"] = dict(default=video_path)
    if with_notification:
        ytdlp_kwargs["progress_hooks"] = ytdlp_kwargs["progress_hooks"] + [notification_hook]
    with YoutubeDL(ytdlp_kwargs) as ydl:
        error_code = ydl.download(url)

    notification.close()
    if error_code != 0:
        raise ConnectionError(f"Download of video with id {id} failed")
    if not Path(video_path).is_file():
        raise FileNotFoundError("Video was downloaded but file is not there")
    with self.engine.begin() as conn:
        conn.execute(
            update(video_table)
            .filter_by(id=id)
            .values(path=video_path)
        )


# TODO: Notification as a decorator for the actual download bit
