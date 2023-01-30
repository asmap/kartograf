# Kartograf

> :warning: **This project is still experimental.**: Be very careful when using files generated from this for any kind of production use.

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

### Check coverage of a mapping file

Check the coverage of a given list of IPs for a given IP prefix to ASN map:

```
./run cov -m /path/to/map_file.txt -l /path/to/ip_list.txt
```
