# Kartograf: IP to ASN mapping for everyone

> :warning: **This project is still experimental.** Be very careful when using files generated from this for any kind of production use.

## Background

Free software projects that maintain a P2P network aim for diversity of peers to protect its users from partitioning and eclipse attacks. To achieve this, they sort peers into buckets. A primitive version of this is bucketing by /16 IP prefixes, but depending on the threat model of the project, bucketing by geographic location or ISP of the peer is more effective. These projects then rely on map files for this supplemental information that may come from providers that are malicious or compromized.

Kartograf is a free software project that generates such map files, for the start IP to AS maps, in a trust-minimized and transparent way. It pulls data from different public sources and combines them in a purely functional way to minimize the possibility of accidental BGP leaks or malicious hijacks ending up in the resulting map. Additionally, the software provides informative, easy-to-parse logging and preserves intermittent artifacts. Projects utilizing Kartograf will then publish this information which allows their users to audit the generation process of the map and verify the integrity of the shipped result file by repeating the process, similar to reproducible build systems.

## Requirements

Kartograf requires `rpki-client` to be installed locally. Find the install instructions on https://www.rpki-client.org/.

Install required Python packages:

```
$ pip3 install -r requirements.txt
```

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
