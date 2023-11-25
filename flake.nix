{
  description = "An IP-to-AS mapping tool.";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-23.05";
    utils.url = "github:numtide/flake-utils";
    # the rpki-client binary will be built from the flake at this URL.
    rpki-cli.url = "github:fjahr/rpki-client-nix";
  };

  outputs = {
    self,
    nixpkgs,
    utils,
    rpki-cli,
  }:
    # Build for all default systems: ["x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin"]
    utils.lib.eachDefaultSystem (system: let
      pkgs = nixpkgs.legacyPackages.${system};
    in rec {
      # This flake exposes one attribute: a development shell
      # containing the rpki-client and the necessary Python env and packages to run kartograf.
      # To use, run 'nix develop' in the current directory.
      devShell = pkgs.mkShell {
          packages = [
            rpki-cli.defaultPackage.${system}
            # Python 3.10 with packages
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
