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
        if isinstance(ip, (ipaddress.IPv4Network, ipaddress.IPv6Network)):
            return self._lookup_network(ip)
        if isinstance(ip, (ipaddress.IPv4Address, ipaddress.IPv6Address)):
            return self._lookup_address(ip)
        raise TypeError("lookup expects an ip_address or ip_network object")

    def _check_subtree(self, node):
        '''
        Check if subtree contains any networks recursively.
        '''
        if node.asn is not None:
            result = node.asn
        for bit in [0, 1]:
            if node.children[bit] is not None:
                result = self._check_subtree(node.children[bit])
                if result is not None:
                    return result
        return None

    def _lookup_address(self, ip):
        """Lookup an IP address using longest prefix match."""
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

    def _lookup_network(self, network):
        """Lookup an IP network and check for overlap with existing networks.

        For RPKI-based merging, we consider a network 'included' if it overlaps
        with any RPKI network (exact match, subset, or superset). We only want
        to add networks from less trusted sources if they don't overlap at all.
        """
        if network.version == 4:
            root = self._ipv4_root
            max_bits = 32
        else:
            root = self._ipv6_root
            max_bits = 128

        addr_int = int(network.network_address)
        prefix_len = network.prefixlen

        node = root
        last_asn = None

        # Traverse the trie to find RPKI networks that contain this candidate network
        for i in range(max_bits):
            if i<= prefix_len:
                if node.asn is not None:
                    last_asn = node.asn

                bit = (addr_int >> (max_bits - 1 - i)) & 1
                if node.children[bit] is None:
                    break
                node = node.children[bit]

        # a network exists containing the candidate network
        if last_asn is not None:
            return last_asn

        # exact match -- the candidate network is already included
        if node.asn is not None:
            return node.asn

        # check if any networks would be overlapped by the candidate network
        return self._check_subtree(node)

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
