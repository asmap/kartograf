import ipaddress

class TrieNode:
    '''
    A node of the trie: children, and the ASN value associated with the node.
    '''
    __slots__ = ('children', 'asn')

    def __init__(self):
        self.children = [None, None]
        self.asn = None


class IPTrie:
    '''
    A trie representing IP networks and their associated asn.
    The trie has two roots: one for IPv4 addresses, one for IPv6.
    '''
    def __init__(self):
        self._ipv4_root = TrieNode()
        self._ipv6_root = TrieNode()

    def insert(self, network, asn):
        if not isinstance(network, (ipaddress.IPv4Network, ipaddress.IPv6Network)):
            raise TypeError("lookup expects an ip_address object")

        if network.version == 4:
            root = self._ipv4_root
            max_bits = 32
        else:
            root = self._ipv6_root
            max_bits = 128

        addr_int = int(network.network_address)
        prefix_len = network.prefixlen

        node = root
        for i in range(prefix_len):
            bit = (addr_int >> (max_bits - 1 - i)) & 1
            if node.children[bit] is None:
                node.children[bit] = TrieNode()
            node = node.children[bit]

        node.asn = asn

    def lookup(self, ip):
        if not isinstance(ip, (ipaddress.IPv4Address, ipaddress.IPv6Address)):
            raise TypeError("lookup expects an ip_address object")

        if ip.version == 4:
            root = self._ipv4_root
            max_bits = 32
        else:
            root = self._ipv6_root
            max_bits = 128

        addr_int = int(ip)
        last_asn = None
        node = root

        for i in range(max_bits):
            if node.asn is not None:
                last_asn = node.asn
            bit = (addr_int >> (max_bits - 1 - i)) & 1
            if node.children[bit] is None:
                break
            node = node.children[bit]

        if node.asn is not None:
            last_asn = node.asn

        return last_asn

    def from_map_file(self, map_file):
        for line in map_file:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                prefix, asn = parts[0], parts[1]
                try:
                    _, number = asn.split("AS")
                    int(number)
                    network = ipaddress.ip_network(prefix)
                except ValueError:
                    raise ValueError(f"Invalid ASN or network provided: {prefix}, {asn}\nPlease remove and re-run.")

                self.insert(network, asn)
