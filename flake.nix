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
          feedparser
          ipython
          pandas
          sqlalchemy
          sqlite-utils
          yt-dlp
          pygobject3
        ];
      myPython = pkgs.python3.withPackages pythonPkgs;
    in {
      devShells.${system}.default = pkgs.mkShell {
        buildInputs = with pkgs; [
          myPython
          gtk4
          sqlite-utils
          gobject-introspection
          libadwaita
        ];
      };
    };
}
