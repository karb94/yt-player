# from yt_dlp import YoutubeDL
from urllib.request import urlretrieve
from pathlib import Path

formats_ranking = (
    "bestvideo[width=2560][vcodec=vp9]+bestaudio",
    "bestvideo[width=2560]+bestaudio",
    "bestvideo[width<=2560]+bestaudio",
    "best",
)
OPTIONS = {
    "format": "/".join(formats_ranking)
}
# https://github.com/yt-dlp/yt-dlp/blob/b6951271ac014761c9c317b9cecd5e8e139cfa7c/yt_dlp/utils/_utils.py#L2781
OUTTMPL_TYPES = {
    'pl_video': "%(id)s.%(ext)s",
}
MERGE_OUTPUT_FORMAT = "mkv"

# url = "https://www.youtube.com/watch?v=xSqol6GQRJw.jpg"

# def download_video(url: str):
#     with YoutubeDL() as ydl:
#         error_code = ydl.download(url)

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

