# Why Nix

Our recommended method for running kartograf is via Nix.

This repo exposes a development shell via a Nix flake. This means that you can clone the repo, run `nix develop` and have all the dependencies (RPKI client, Python, etc) you need to run kartograf.

It also allows us, the developers, to enforce certain versions of these tools across target systems.
Kartograf is intended to produce an IP-to-AS map (ASmap) from a set of data, and we've put effort into making this output deterministic, meaning that every run with the same data should produce the same output. In order to ensure the generation of this ASmap is deterministic and reproducible, we need to remove variability in the software we use such as the Python version, Python deps, or the rpki-client version. This also helps us understand whether new releases of the RPKI client change the resulting ASmap.

The status quo is to hope every package manager (Brew, Pacman, Yum, APT etc) is:
- keeping up to date with new releases
- maintaining old releases
- not doing adhoc, unpredictable stuff of the user's OS, dependent on the target arch

But this is almost never the case. And Nix fixes this.

We pin the packages we expose to specific version. The `rpki-client` version is set by our own nix-ified [rpki-client](https://github.com/fjahr/rpki-client-nix) repo. We pin the nixpkgs version so that we know that every user will be getting the same version of Python and its deps. If you want to run an older version as we roll forward, you can just check out the appropriate git commit and `nix develop` from there.

If you have any questions or difficulty getting started, feel free to open an issue!
