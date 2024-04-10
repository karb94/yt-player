from pathlib import Path
from yt_dlp import YoutubeDL
from urllib.request import urlretrieve
from pprint import pp
from collections.abc import Callable
from typing import Any, Optional
import requests
from bs4 import BeautifulSoup
import re

import gi
gi.require_version("Notify", "0.7")
from gi.repository import GLib, Notify # type: ignore[attr-defined]

get_thumbnail_url = "http://img.youtube.com/vi/{video_id}/mqdefault.jpg".format
get_video_url = "http://www.youtube.com/watch?v={video_id}".format

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

def download_thumbnail(video_id: str, path: str) -> None:
    p = Path(path)
    if not p.parent.is_dir():
        raise FileNotFoundError(f"Directory {p.parent} does not exist or is not a directory")
    if p.exists():
        raise FileExistsError(f"File {p} already exists")
    url = get_thumbnail_url(video_id=video_id)
    urlretrieve(url, path)


def parse_progress(download: dict[str, Any]) -> float | None:
    # print(progress["status"])
    if "info_dict" in download:
        del download["info_dict"]
    # if progress["status"] == "
    if "fragment_count" in download and "fragment_index" in download:
        if download["fragment_index"] > download["fragment_count"]+1:
            pp(download)
            raise KeyError(f"No keys to calculate errors. Keys available {download.keys()}")
        else:
            progress = download["fragment_index"] / (download["fragment_count"]+1)
    elif all(k in download for k in ("downloaded_bytes", "total_bytes")):
        progress = download["downloaded_bytes"] / download["total_bytes"]
    elif all(k in download for k in ("downloaded_bytes", "total_bytes_estimate")):
        progress = download["downloaded_bytes"] / download["total_bytesestimate"]
    elif "fragment_count" in download and "fragment_index" in download:
        if download["fragment_index"] > download["fragment_count"]:
            pp(download)
            raise KeyError(f"No keys to calculate errors. Keys available {download.keys()}")
        else:
            progress = download["fragment_index"] / (download["fragment_count"]+1)
    else:
        return None
    # progress = download["downloaded_bytes"] / download["total_bytes"]
    # eta = download["eta"]
    # speed = download["speed"]
    # elapsed = download["elapsed"]
    return progress


def get_notification_hook(notification: Notify.Notification) -> Callable[[dict[str, Any]], None]:
    def notification_hook(d: dict[str, Any]) -> None:
        progress_frac = parse_progress(d)
        if isinstance(progress_frac, float):
            value = GLib.Variant.new_uint32(int(progress_frac*100))
            notification.set_hint("value", value)
            # fgcolor = GLib.Variant.new_string("#ff4444")
            # notification.set_hint("fgcolor", fgcolor)
            notification.show()
    return notification_hook


def download_video(
    url: str,
    path: str,
    notification: Optional[Notify.Notification] = None,
    **ytdlp_kwargs: Any,
) -> None:
    p = Path(path)
    if p.is_file():
        raise FileExistsError
    p.parent.mkdir(parents=True, exist_ok=True)
    ytdlp_kwargs["outtmpl"] = dict(default=path)

    if notification is not None:
        notification.show()
        notification_hook = get_notification_hook(notification)
        ytdlp_kwargs["progress_hooks"] = ytdlp_kwargs["progress_hooks"] + [notification_hook]

    with YoutubeDL(ytdlp_kwargs) as ydl:
        error_code = ydl.download(url)

    if notification is not None:
        notification.close()

    if error_code != 0:
        raise ConnectionError(f"Download of video with id {id} failed")
    if not p.is_file():
        raise FileNotFoundError("Video was downloaded but file is not there")


def get_yt_channel_id(modern_url: str) -> str:
    content = requests.get(modern_url).content
    soup = BeautifulSoup(content, "html.parser")
    channel_id_regex = re.compile(r'"channelId":"([\w-]{24})"')
    for script in soup.find_all("script"):
        if script.string is None:
            continue
        match = channel_id_regex.search(script.string)
        if match is not None:
            return match.group(1)
    raise ValueError(f"Could not find a channelId in URL {modern_url}")

