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
            raise TypeError("insert expects an ip_network object")

        node, _ = self._walk(network.version, int(network.network_address),
                             bits=network.prefixlen, create=True)
        node.asn = asn

    def lookup(self, ip):
        """Lookup an IP address using longest prefix match."""
        if not isinstance(ip, (ipaddress.IPv4Address, ipaddress.IPv6Address)):
            raise TypeError("lookup expects an ip_address object")

        _, last_asn = self._walk(ip.version, int(ip))
        return last_asn

    def covering_asn(self, network):
        """Return the ASN of the network covering this one (exact match or
        superset), or None.

        For RPKI-based merging, we consider a network 'included' if it is
        covered by an existing network (exact match or subset). We only want
        to add networks from less trusted sources if they don't overlap at all.
        """
        if not isinstance(network, (ipaddress.IPv4Network, ipaddress.IPv6Network)):
            raise TypeError("covering_asn expects an ip_network object")

        _, last_asn = self._walk(network.version, int(network.network_address),
                                 bits=network.prefixlen)
        return last_asn

    def _walk(self, version, addr_int, bits=None, create=False):
        """Walk the trie along the bit path of addr_int.

        Walks up to `bits` levels (default: every level, stopping when the
        path runs out of children). With create=True, extends the path with
        new nodes instead of stopping. Returns (node, last_asn): the node
        where the walk stopped, and the ASN of the deepest node with an ASN
        seen along the path.
        """
        if version == 4:
            node = self._ipv4_root
            max_bits = 32
        else:
            node = self._ipv6_root
            max_bits = 128

        last_asn = node.asn
        for i in range(max_bits if bits is None else bits):
            bit = (addr_int >> (max_bits - 1 - i)) & 1
            child = node.children[bit]
            if child is None:
                if not create:
                    break
                child = TrieNode()
                node.children[bit] = child
            node = child
            if node.asn is not None:
                last_asn = node.asn

        return node, last_asn

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
