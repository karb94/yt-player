{
  description = "yt-player";
  nixConfig.bash-prompt-prefix = "\n[nix develop]";
  inputs = { nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable"; };
  outputs = { self, nixpkgs, ... }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      pythonPkgs = ps:
        with ps; [
          feedparser
          pandas
          yt-dlp
          ipython
          sqlite-utils
          sqlalchemy
        ];
      python = pkgs.python3.withPackages pythonPkgs;
    in {
      devShells.${system}.default = pkgs.mkShell { buildInputs = [ python ]; };
    };
}
