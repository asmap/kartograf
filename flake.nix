{
  description = "An IP-to-AS mapping tool.";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.11";
    # the rpki-client binary will be built from the flake at this URL.
    rpki-cli.url = "github:asmap/rpki-client-nix";
    rpki-cli.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = {
    self,
    nixpkgs,
    rpki-cli,
  }: let
    forAllSystems = nixpkgs.lib.genAttrs [
      "x86_64-linux"
      "aarch64-linux"
      "x86_64-darwin"
      "aarch64-darwin"
    ];

    nixpkgsFor = system: import nixpkgs { inherit system;};
  in {
    # This flake exposes the following attributes:
    # * A development shell containing the rpki-client and the necessary
    #   Python env and packages to run kartograf. To use, run 'nix develop'
    #   in the current directory.
    # * A default/kartograf package
    # * A NixOS module
    devShells.default = forAllSystems (system: let
      pkgs = nixpkgsFor system;
      pythonDevDeps = pkgs.python311.withPackages (ps: [
        ps.beautifulsoup4
        ps.pandas
        ps.pylint
	ps.pytest
        ps.requests
        ps.tqdm
      ]);
    in
      pkgs.mkShell {
        packages = [pythonDevDeps rpki-cli.defaultPackage.${system}];
      });

    packages = forAllSystems (system: let
      pkgs = nixpkgsFor system;
    in rec {
      kartograf = pkgs.callPackage ./nix/package.nix {
        rpki-client = rpki-cli.defaultPackage.${system};
      };
      default = kartograf;
    });

    nixosModules.default = import ./nix/module.nix;
  };
}
