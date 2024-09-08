{
  description = "yt-player";
  nixConfig.bash-prompt-prefix = ''

    [nix develop]'';
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };
  outputs =
    { nixpkgs, ... }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      pythonPkgs =
        ps: with ps; [
          aiofiles
          aiohttp
          aiosqlite
          beautifulsoup4
          feedparser
          ipython
          mypy
          pandas
          pandas-stubs
          pydantic
          pygobject-stubs
          pygobject3
          pytest
          pytest-asyncio
          pytest-bdd
          pyxdg
          requests
          sqlalchemy
          sqlite-utils
          types-beautifulsoup4
          types-python-dateutil
          types-requests
          xdg-base-dirs
          yt-dlp
        ];
      myPython = pkgs.python3.withPackages pythonPkgs;
      external_pkgs = with pkgs; [
        ffmpeg
        gobject-introspection
        # gsettings-desktop-schemas
        gtk4
        libadwaita
        libnotify
        sqlite-utils
      ];
    in
    {
      devShells.${system}.default = pkgs.mkShellNoCC {
        packages = external_pkgs ++ [ myPython ];
        shellHook = ''
          export PYTHONPATH="''${PYTHONPATH}:src"
        '';
      };
    };
}
