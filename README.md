# Kartograf: IP to ASN mapping for everyone

> :warning: **This project is still experimental.** Be very careful when using files generated from this for any kind of production use.

## Background

Free software projects that maintain a P2P network aim for diversity of peers to protect its users from partitioning and eclipse attacks. To achieve this, they sort peers into buckets. A primitive version of this is bucketing by /16 IP prefixes, but depending on the threat model of the project, bucketing by geographic location or ISP of the peer is more effective. These projects then rely on map files for this supplemental information that may come from providers that are malicious or compromized.

Kartograf is a free software project that generates such map files, for the start IP to AS maps, in a trust-minimized and transparent way. It pulls data from different public sources and combines them in a purely functional way to minimize the possibility of accidental BGP leaks or malicious hijacks ending up in the resulting map. Additionally, the software provides informative, easy-to-parse logging and preserves intermittent artifacts. Projects utilizing Kartograf will then publish this information which allows their users to audit the generation process of the map and verify the integrity of the shipped result file by repeating the process, similar to reproducible build systems.

## Requirements

The recommended method of installation is with [Nix](https://nixos.org/download.html). You can read about why [here](./nix.md). You may however install from any method below.

### Nix

The Nix flake in this repo exposes a development shell, with the `rpki-client` binary, Python 3.10, and the Python packages required to run kartograf.

If you have Nix installed with flakes enabled, clone this repo, and run `nix develop`. You can now proceed to [Usage](#usage).

If you don't have flakes enabled, you can either:
- pass the flag `--experimental-features 'nix-command flakes'` whenever you run `nix develop`
- or add the following line to `~/.config/nix/nix.conf`:
```
experimental-features = nix-command flakes
```

to enable flakes in your Nix config, then run `nix develop`.

### Linux/BSD/macOS

#### rpki-client

Kartograf requires `rpki-client` version 8.4 or higher to be installed locally. Many package managers have `rpki-client`, however please note that typically only the latest version is available. Kartograf is currently tested to work with `rpki-client` 8.4 - 8.6. If a new release is available that breaks compatibility, you may need to build a compatible `rpki-client` version yourself if your preferred package manager does not have a compatible version available. In that case, see the [instructions in the rpki-client-portable project](https://github.com/rpki-client/rpki-client-portable/blob/master/INSTALL).

```
# Linux/BSD
$ {pkg,dnf,yum,apt} install rpki-client
# macOS
$ brew install rpki-client
```

#### Python dependencies

Python versions 3.10 and 3.11 have both been tested with Kartograf.

You can use `pip3` to install required Python packages:

```
$ pip3 install -r requirements.txt
```

### Windows

Kartograf has not been tested on Windows.

## Usage

### Building IP prefix to ASN maps

Please be aware that the full process currently takes about 6 hours with an M1 Macbook Pro and fiber optic connection.

Generate a fresh map of IP prefix to ASN using only RPKI:

```
./run map
```

You can enhance the RPKI maps with RIRs IRR data or Routeviews data using the `-irr` and `-rv` flags:

```
./run map -rv
```

### Reproducing IP prefix to ASN maps

This uses an pre-existing data folder and creates a map from it, allowing to reproduce map files. The posix timestamp needs to be provided as well and it needs to match the epoch of the initial run exactly, otherwise the resulting file will be different.

```
./run map -r /path/to/data -t 1698854940
```

### Merging IP prefix to ASN maps

This merges on map into another map. The mappings of the base file have preference over those in the extra file.

```
./run merge -b /path/to/base_file.txt -e /path/to/extra_file.txt -o /path/to/output.txt
```

### Check coverage of a mapping file

Check the coverage of a given list of IPs for a given IP prefix to ASN map:

```
./run cov -m /path/to/map_file.txt -l /path/to/ip_list.txt
```

## File format examples

Kartograf expects files input files to be in the following formatting and also produces output files that follow this format.

### Map files

```
103.152.34.0/23 AS14618
2406:4440:10::/44 AS142641
2406:4440:f000::/44 AS38173
103.152.35.0/24 AS38008
```

### IP lists

```
2.56.241.243
2.56.98.121
2001:067c:06ec:0203:0218:33ff:fe44:5528
2001:067c:0750:0000:0000:0000:0010:0001
```

## Acknowledgements

[Job Snijders](https://twitter.com/JobSnijders)
