{
  description = "An IP-to-AS mapping tool.";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-23.05";
    utils.url = "github:numtide/flake-utils";
    rpki-cli.url = "github:fjahr/rpki-client-nix";
  };

  outputs = {
    self,
    nixpkgs,
    utils,
    rpki-cli,
  }:
    utils.lib.eachDefaultSystem (system: let
      pkgs = nixpkgs.legacyPackages.${system};
    in rec {
      devShell = pkgs.mkShell {
          packages = [
            rpki-cli.defaultPackage.${system}
            (pkgs.python310.withPackages (ps: [
              ps.pandas
              ps.beautifulsoup4
              ps.requests
              ps.tqdm
            ]))
          ];
      };
    });
}
