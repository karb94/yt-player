{
  description = "yt-player";
  nixConfig.bash-prompt-prefix = ''

    [nix develop]'';
  inputs = { nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable"; };
  outputs = { self, nixpkgs, ... }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      pythonPkgs = ps:
        with ps; [
          beautifulsoup4
          feedparser
          ipython
          mypy
          pandas
          # pandas-stubs
          pygobject-stubs
          pygobject3
          pyxdg
          requests
          sqlalchemy
          sqlite-utils
          types-python-dateutil
          yt-dlp
        ];
      myPython = pkgs.python3.withPackages pythonPkgs;
    in {
      devShells.${system}.default = pkgs.mkShell {
        buildInputs = with pkgs; [
          ffmpeg
          gobject-introspection
          gtk4
          libadwaita
          libnotify
          myPython
          sqlite-utils
        ];
      };
    };
}
