with import <nixpkgs> { };
(python3.withPackages (ps: with ps; [
  feedparser
  pandas
  yt-dlp
  ipython
  sqlite-utils
  sqlalchemy
])).env
