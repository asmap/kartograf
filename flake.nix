{
  description = "An IP-to-AS mapping tool.";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05";
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
    # Add a kartograf module for NixOS (see module.nix for details)
    { nixosModules.kartograf = import ./module.nix self; } //
    # Build for all default systems: ["x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin"]
    utils.lib.eachDefaultSystem (system: let
      pkgs = nixpkgs.legacyPackages.${system};

      # Custom derivation for pandarallel
      pandarallel = pkgs.python3Packages.buildPythonPackage rec {
        pname = "pandarallel";
        version = "1.6.5";

        src = pkgs.python311Packages.fetchPypi {
          inherit pname version;
          sha256 = "HC35j/ZEHorhP/QozuuqfsQtcx9/lyxBzk/e8dOt9kA=";
        };

        propagatedBuildInputs = with pkgs.python3Packages; [ pandas dill psutil ];

        meta = with pkgs.lib; {
          description = "An efficient parallel computing library for pandas";
          homepage = "https://github.com/nalepae/pandarallel";
          license = licenses.bsd3;
        };
      };
      kartografDeps = [
        rpki-cli.defaultPackage.${system}
        (pkgs.python311.withPackages (ps: [
          ps.pandas
          ps.beautifulsoup4
          ps.numpy
          ps.requests
          ps.tqdm
          pandarallel
        ]))
      ];

    in {
      # This flake exposes the following attributes:
      # * A development shell containing the rpki-client and the necessary
      #   Python env and packages to run kartograf. To use, run 'nix develop'
      #   in the current directory.
      # * A default/kartograf package 
      # * A NixOS module
      devShell = pkgs.mkShell {
        packages = kartografDeps;
      };
      packages = {
        kartograf = pkgs.stdenv.mkDerivation { # not a python-installable package, so just manually copy files
          pname = "kartograf";
          version = "1.0.0";
          src = ./.;
          nativeBuildInputs = [ pkgs.makeWrapper ];
          buildInputs = kartografDeps;
          propagatedBuildInputs = [ rpki-cli.defaultPackage.${system} ];
          buildPhase = ''
            mkdir -p $out/lib/kartograf
            cp -r ${./kartograf}/* $out/lib/kartograf/
          '';
          installPhase = ''
            mkdir -p $out/bin
            cp ${./run} $out/bin/kartograf
            chmod +x $out/bin/kartograf
          '';
          fixupPhase = ''
            wrapProgram $out/bin/kartograf \
              --set PYTHONPATH $out/lib:$PYTHONPATH
            wrapProgram $out/bin/kartograf \
              --set PATH ${rpki-cli.defaultPackage.${system}}/bin:$PATH
          '';
          meta = with pkgs.lib; {
            description = "Kartograf: IP to ASN mapping for everyone";
            license = licenses.mit;
            homepage = "https://github.com/fjahr/kartograf";
          };
        };
        default = self.packages.${system}.kartograf;
      };
    });
}
