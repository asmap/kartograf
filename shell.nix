{pkgs ? import <nixpkgs> {}}:

let
    rpki-client = import (builtins.fetchGit {
        url = "https://github.com/fjahr/rpki-client-nix.git";
        rev = "9d1c2e8bcaf15eff425385ab6494eac195434cc9";
    }) {};
in
pkgs.mkShell {
  packages = [
    rpki-client
    (pkgs.python3.withPackages (ps: [
      ps.pandas
      ps.beautifulsoup4
      ps.requests
      ps.tqdm
    ]))
  ];
}
