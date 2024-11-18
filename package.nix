{pkgs, rpki-client }:
let
      pythonBuildDeps = pkgs.python311.withPackages (ps: [
        ps.beautifulsoup4
        ps.pandas
        ps.requests
        ps.tqdm
      ]);
in
        pkgs.stdenv.mkDerivation {
          # not a python-installable package, so just manually copy files
          pname = "kartograf";
          version = "1.0.0";
          src = ./.;
          nativeBuildInputs = [pkgs.makeWrapper];
          buildInputs = [ pythonBuildDeps ];
          propagatedBuildInputs = [ rpki-client ];
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
              --set PATH ${rpki-client}/bin:$PATH
          '';
          meta = with pkgs.lib; {
            description = "Kartograf: IP to ASN mapping for everyone";
            license = licenses.mit;
            homepage = "https://github.com/asmap/kartograf";
          };
        }
