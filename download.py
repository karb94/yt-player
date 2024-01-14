from yt_dlp import YoutubeDL
from urllib.request import urlretrieve
from pathlib import Path
from pprint import pp
from collections.abc import Callable

FORMATS_RANKING = (
    "bestvideo[width=2560][vcodec=vp09.00.50.08][ext=mp4]+bestaudio",
    "bestvideo[width=2560][vcodec=vp9][ext=mp4]+bestaudio",
    "bestvideo[width=2560][vcodec=vp09.00.50.08]+bestaudio",
    "bestvideo[width=2560]+bestaudio",
    "bestvideo[width<=2560]+bestaudio",
    "best",
)

url = "https://www.youtube.com/watch?v=7DKv5H5Frt0"

def parse_progress(download: dict):
    # print(progress["status"])
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
        return 'NO PROGRESS'
        
    # progress = download["downloaded_bytes"] / download["total_bytes"]
    # eta = download["eta"]
    # speed = download["speed"]
    # elapsed = download["elapsed"]
    return progress

def download_video(url: str, directory: str, progress_hook: Callable):
    options = {
        "format": "/".join(FORMATS_RANKING),
        "outtmpl": dict(default=f"{directory}/%(id)s.%(ext)s"),
        "merge_output_format": "mkv",
        "noprogress": True,
        "progress_hooks": [progress_hook],
    }
    with YoutubeDL(options) as ydl:
        return ydl.download(url)

get_thumbnail_url = "http://img.youtube.com/vi/{video_id}/mqdefault.jpg".format

def download_thumbnail(video_id: str, dir: str) -> str:
    thumbnail_dir = Path(dir)
    thumbnail_dir.mkdir(parents=True, exist_ok=True)
    url = get_thumbnail_url(video_id=video_id)
    ext = Path(url).suffix
    filename = video_id + ext
    thumbnail_path = thumbnail_dir / filename
    urlretrieve(url, thumbnail_path)
    return str(thumbnail_path)

