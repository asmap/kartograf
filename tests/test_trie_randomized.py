"""
Randomized tests for IPTrie, ported from ASMap test patterns.

These tests use randomized data to verify the trie behaves correctly
across a wide range of inputs.
"""
import ipaddress
import random
from kartograf.trie import IPTrie


def test_ipv4_prefix_roundtrips():
    """Test that random IPv4 networks can be inserted and looked up correctly."""
    for _ in range(100):
        trie = IPTrie()
        net_bits = random.getrandbits(32)
        for prefix_len in range(0, 33):
            # Create a properly masked network
            masked_bits = (net_bits >> (32 - prefix_len)) << (32 - prefix_len)
            net = ipaddress.IPv4Network((masked_bits.to_bytes(4, 'big'), prefix_len))
            asn = f"AS{random.randint(1, 65535)}"

            trie.insert(net, asn)

            # Verify we can look up addresses within this network
            # Generate a random address within the network
            if prefix_len < 32:
                host_bits = random.getrandbits(32 - prefix_len)
                addr_int = masked_bits | host_bits
            else:
                addr_int = masked_bits
            addr = ipaddress.IPv4Address(addr_int)

            result = trie.lookup(addr)
            assert result == asn, f"Lookup failed for {addr} in {net}"

def test_ipv6_prefix_roundtrips():
    """Test that random IPv6 networks can be inserted and looked up correctly."""
    for _ in range(20):
        trie = IPTrie()
        net_bits = random.getrandbits(128)
        for prefix_len in range(0, 129):
            # Create a properly masked network
            masked_bits = (net_bits >> (128 - prefix_len)) << (128 - prefix_len)
            net = ipaddress.IPv6Network((masked_bits.to_bytes(16, 'big'), prefix_len))
            asn = f"AS{random.randint(1, 65535)}"

            trie.insert(net, asn)

            # Verify we can look up addresses within this network
            if prefix_len < 128:
                host_bits = random.getrandbits(128 - prefix_len)
                addr_int = masked_bits | host_bits
            else:
                addr_int = masked_bits
            addr = ipaddress.IPv6Address(addr_int)

            result = trie.lookup(addr)
            assert result == asn, f"Lookup failed for {addr} in {net}"

def test_longest_prefix_match_random_ipv4():
    """Test longest prefix matching with random nested IPv4 networks."""
    for _ in range(50):
        trie = IPTrie()
        # Generate a base network with random prefix length between 8 and 20
        base_prefix_len = random.randint(8, 20)
        base_bits = random.getrandbits(32)
        base_masked = (base_bits >> (32 - base_prefix_len)) << (32 - base_prefix_len)
        base_net = ipaddress.IPv4Network((base_masked.to_bytes(4, 'big'), base_prefix_len))

        # Insert the base network
        base_asn = "AS12345"
        trie.insert(base_net, base_asn)

        # Insert more specific networks within the base, tracking all
        all_networks = [(base_net, base_asn)]
        for i in range(3):
            # Each specific network is more specific than the base
            spec_prefix_len = min(base_prefix_len + (i + 1) * 4, 32)
            spec_masked = (base_bits >> (32 - spec_prefix_len)) << (32 - spec_prefix_len)
            spec_net = ipaddress.IPv4Network((spec_masked.to_bytes(4, 'big'), spec_prefix_len))
            spec_asn = f"AS{i}"
            trie.insert(spec_net, spec_asn)
            all_networks.append((spec_net, spec_asn))

        # Test lookups - should return the most specific match
        for test_net, _ in all_networks:
            addr_int = int(test_net.network_address)
            addr = ipaddress.IPv4Address(addr_int)

            # Find the expected most specific network containing this address
            best_asn = None
            best_prefix_len = -1
            for net, asn in all_networks:
                if addr in net and net.prefixlen > best_prefix_len:
                    best_asn = asn
                    best_prefix_len = net.prefixlen

            result = trie.lookup(addr)
            assert result == best_asn, f"Expected {best_asn} for {addr}, got {result}"

def test_longest_prefix_match_random_ipv6():
    """Test longest prefix matching with random nested IPv6 networks."""
    for _ in range(20):
        trie = IPTrie()
        # Generate a base network with random prefix length between 16 and 64
        base_prefix_len = random.randint(16, 64)
        base_bits = random.getrandbits(128)
        base_masked = (base_bits >> (128 - base_prefix_len)) << (128 - base_prefix_len)
        base_net = ipaddress.IPv6Network((base_masked.to_bytes(16, 'big'), base_prefix_len))

        # Insert the base network
        base_asn = "AS12345"
        trie.insert(base_net, base_asn)

        # Insert more specific networks within the base, tracking all
        all_networks = [(base_net, base_asn)]
        for i in range(3):
            spec_prefix_len = min(base_prefix_len + (i + 1) * 8, 128)
            spec_masked = (base_bits >> (128 - spec_prefix_len)) << (128 - spec_prefix_len)
            spec_net = ipaddress.IPv6Network((spec_masked.to_bytes(16, 'big'), spec_prefix_len))
            spec_asn = f"AS{i}"
            trie.insert(spec_net, spec_asn)
            all_networks.append((spec_net, spec_asn))

        # Test lookups - should return the most specific match
        for test_net, _ in all_networks:
            addr_int = int(test_net.network_address)
            addr = ipaddress.IPv6Address(addr_int)

            # Find the expected most specific network containing this address
            best_asn = None
            best_prefix_len = -1
            for net, asn in all_networks:
                if addr in net and net.prefixlen > best_prefix_len:
                    best_asn = asn
                    best_prefix_len = net.prefixlen

            result = trie.lookup(addr)
            assert result == best_asn, f"Expected {best_asn} for {addr}, got {result}"

def test_update_overwrites_correctly():
    """Test that updating (re-inserting) a network overwrites the ASN."""
    for _ in range(50):
        trie = IPTrie()
        # Random IPv4 network
        net_bits = random.getrandbits(32)
        prefix_len = random.randint(8, 28)
        masked_bits = (net_bits >> (32 - prefix_len)) << (32 - prefix_len)
        net = ipaddress.IPv4Network((masked_bits.to_bytes(4, 'big'), prefix_len))

        # Insert with initial ASN
        initial_asn = "AS12345"
        trie.insert(net, initial_asn)

        # Generate test address
        addr = ipaddress.IPv4Address(masked_bits)
        assert trie.lookup(addr) == initial_asn

        # Update with new ASN
        new_asn = "AS6789"
        trie.insert(net, new_asn)
        assert trie.lookup(addr) == new_asn

def test_disjoint_networks_dont_interfere():
    """Test that disjoint networks don't affect each other's lookups."""
    for _ in range(30):
        trie = IPTrie()
        networks = []

        # Insert several disjoint /24 networks
        for i in range(5):
            # Use different first octets to ensure disjoint
            first_octet = (i * 50) % 256
            net = ipaddress.IPv4Network(f"{first_octet}.0.0.0/8")
            asn = f"AS{i}"
            trie.insert(net, asn)
            networks.append((net, asn))

        # Verify each network's lookups are independent
        for net, expected_asn in networks:
            # Address within network
            addr_in = ipaddress.IPv4Address(int(net.network_address) + 1)
            assert trie.lookup(addr_in) == expected_asn

            # Address just outside should return different ASN or None
            # (depending on if adjacent network exists)

def test_mixed_ipv4_ipv6_independence():
    """Test that IPv4 and IPv6 entries are completely independent."""
    for _ in range(20):
        trie = IPTrie()

        # Insert random IPv4 networks
        ipv4_insertions = []
        for _ in range(5):
            net_bits = random.getrandbits(32)
            prefix_len = random.randint(8, 24)
            masked_bits = (net_bits >> (32 - prefix_len)) << (32 - prefix_len)
            net = ipaddress.IPv4Network((masked_bits.to_bytes(4, 'big'), prefix_len))
            asn = f"AS4{random.randint(1, 1000)}"
            trie.insert(net, asn)
            ipv4_insertions.append((net, asn))

        # Insert random IPv6 networks
        ipv6_insertions = []
        for _ in range(5):
            net_bits = random.getrandbits(128)
            prefix_len = random.randint(16, 64)
            masked_bits = (net_bits >> (128 - prefix_len)) << (128 - prefix_len)
            net = ipaddress.IPv6Network((masked_bits.to_bytes(16, 'big'), prefix_len))
            asn = f"AS6{random.randint(1, 1000)}"
            trie.insert(net, asn)
            ipv6_insertions.append((net, asn))

        # Verify IPv4 lookups using longest prefix match
        for test_net, _ in ipv4_insertions:
            addr = ipaddress.IPv4Address(int(test_net.network_address))

            # Find expected: most specific network, last write wins for same prefix
            best_asn = None
            best_prefix_len = -1
            for net, asn in ipv4_insertions:
                if addr in net and net.prefixlen >= best_prefix_len:
                    best_asn = asn
                    best_prefix_len = net.prefixlen

            result = trie.lookup(addr)
            assert result == best_asn, f"IPv4: expected {best_asn}, got {result}"

        # Verify IPv6 lookups using longest prefix match
        for test_net, _ in ipv6_insertions:
            addr = ipaddress.IPv6Address(int(test_net.network_address))

            # Find expected: most specific network, last write wins for same prefix
            best_asn = None
            best_prefix_len = -1
            for net, asn in ipv6_insertions:
                if addr in net and net.prefixlen >= best_prefix_len:
                    best_asn = asn
                    best_prefix_len = net.prefixlen

            result = trie.lookup(addr)
            assert result == best_asn, f"IPv6: expected {best_asn}, got {result}"

def test_patching_behavior():
    """
    Test behavior similar to ASMap patching test.

    Builds up a trie with random networks, then applies patches (more specific
    networks) and verifies that lookups return the correct (most specific) ASN.
    """
    for num_leaves in range(1, 10):
        for asnbits in range(0, 12):
            trie = IPTrie()
            # Track all inserted networks with their ASNs
            # Using a list of (network, asn) to track insertion order
            insertions = []

            # Insert initial random networks
            for _ in range(num_leaves):
                net_bits = random.getrandbits(32)
                prefix_len = random.randint(4, 24)
                masked_bits = (net_bits >> (32 - prefix_len)) << (32 - prefix_len)
                net = ipaddress.IPv4Network((masked_bits.to_bytes(4, 'big'), prefix_len))
                asn = f"AS{random.randint(0, 1 << asnbits)}"
                trie.insert(net, asn)
                insertions.append((net, asn))

            # Apply patches (more specific networks that may overlap)
            for _ in range(5):
                net_bits = random.getrandbits(32)
                prefix_len = random.randint(16, 30)
                masked_bits = (net_bits >> (32 - prefix_len)) << (32 - prefix_len)
                net = ipaddress.IPv4Network((masked_bits.to_bytes(4, 'big'), prefix_len))
                asn = f"AS{random.randint(0, 1 << asnbits)}"
                trie.insert(net, asn)
                insertions.append((net, asn))

            # Verify lookups by checking against our tracked insertions
            # For each network, the lookup should return the ASN of the
            # most specific (longest prefix) network containing the address
            for test_net, _ in insertions:
                test_addr = ipaddress.IPv4Address(int(test_net.network_address))

                # Find the most specific network containing this address
                # Use >= to handle same network inserted multiple times (last write wins)
                best_match = None
                best_prefix_len = -1
                for net, asn in insertions:
                    if test_addr in net and net.prefixlen >= best_prefix_len:
                        best_match = asn
                        best_prefix_len = net.prefixlen

                result = trie.lookup(test_addr)
                assert result == best_match, \
                    f"For {test_addr}: expected {best_match}, got {result}"

def test_boundary_addresses():
    """Test lookups at network boundaries."""
    for _ in range(30):
        trie = IPTrie()

        # Random /24 network
        first_three_octets = random.randint(0, 0xFFFFFF)
        net = ipaddress.IPv4Network(f"{(first_three_octets >> 16) & 0xFF}."
                                    f"{(first_three_octets >> 8) & 0xFF}."
                                    f"{first_three_octets & 0xFF}.0/24")
        asn = "AS12345"
        trie.insert(net, asn)

        # First address in network
        first_addr = ipaddress.IPv4Address(int(net.network_address))
        assert trie.lookup(first_addr) == asn

        # Last address in network
        last_addr = ipaddress.IPv4Address(int(net.broadcast_address))
        assert trie.lookup(last_addr) == asn

        # Address just before network (if not 0.0.0.0)
        if int(net.network_address) > 0:
            before_addr = ipaddress.IPv4Address(int(net.network_address) - 1)
            assert trie.lookup(before_addr) is None

        # Address just after network (if not 255.255.255.255)
        if int(net.broadcast_address) < 0xFFFFFFFF:
            after_addr = ipaddress.IPv4Address(int(net.broadcast_address) + 1)
            assert trie.lookup(after_addr) is None

def test_all_prefix_lengths_ipv4():
    """Test that all IPv4 prefix lengths (0-32) work correctly."""
    for prefix_len in range(0, 33):
        trie = IPTrie()
        net_bits = random.getrandbits(32)
        masked_bits = (net_bits >> (32 - prefix_len)) << (32 - prefix_len)
        net = ipaddress.IPv4Network((masked_bits.to_bytes(4, 'big'), prefix_len))
        asn = f"AS123{prefix_len}"

        trie.insert(net, asn)

        # Test with address in network
        test_addr = ipaddress.IPv4Address(masked_bits)
        assert trie.lookup(test_addr) == asn, f"Failed for prefix length {prefix_len}"

def test_all_prefix_lengths_ipv6():
    """Test that all IPv6 prefix lengths (0-128) work correctly."""
    for prefix_len in range(0, 129):
        trie = IPTrie()
        net_bits = random.getrandbits(128)
        masked_bits = (net_bits >> (128 - prefix_len)) << (128 - prefix_len)
        net = ipaddress.IPv6Network((masked_bits.to_bytes(16, 'big'), prefix_len))
        asn = f"AS123{prefix_len}"

        trie.insert(net, asn)

        # Test with address in network
        test_addr = ipaddress.IPv6Address(masked_bits)
        assert trie.lookup(test_addr) == asn, f"Failed for prefix length {prefix_len}"

def test_large_number_of_networks():
    """Test with a large number of random networks."""
    trie = IPTrie()
    networks = []

    # Insert 1000 random networks
    for _ in range(1000):
        net_bits = random.getrandbits(32)
        prefix_len = random.randint(8, 28)
        masked_bits = (net_bits >> (32 - prefix_len)) << (32 - prefix_len)
        net = ipaddress.IPv4Network((masked_bits.to_bytes(4, 'big'), prefix_len))
        asn = f"AS{random.randint(1, 65535)}"
        trie.insert(net, asn)
        networks.append((net, asn))

    # Verify a sample of lookups
    for net, _ in random.sample(networks, min(100, len(networks))):
        addr = ipaddress.IPv4Address(int(net.network_address))
        result = trie.lookup(addr)
        # Result should be some ASN (might not be the one we inserted
        # if a more specific network was added later)
        assert result is not None or any(
            addr in n for n, _ in networks
        ) is False

def test_deeply_nested_networks():
    """Test with deeply nested networks (many levels of specificity)."""
    trie = IPTrie()

    # Create a chain of increasingly specific networks
    # 10.0.0.0/8 -> 10.0.0.0/16 -> 10.0.0.0/24 -> 10.0.0.0/32
    for prefix_len in range(8, 33):
        net = ipaddress.IPv4Network(f"10.0.0.0/{prefix_len}")
        asn = f"AS{prefix_len}"
        trie.insert(net, asn)

    # Lookup 10.0.0.0 should return the most specific (/32)
    addr = ipaddress.IPv4Address("10.0.0.0")
    assert trie.lookup(addr) == "AS32"

    # Lookup 10.0.0.1 should return /31 (10.0.0.0/31 covers .0 and .1)
    addr = ipaddress.IPv4Address("10.0.0.1")
    assert trie.lookup(addr) == "AS31"

    # Lookup 10.0.0.2 should return /30 (10.0.0.0/30 covers .0-.3)
    addr = ipaddress.IPv4Address("10.0.0.2")
    assert trie.lookup(addr) == "AS30"

    # 10.128.0.0 is only covered by /8 (outside of /9 since 10.0.0.0/9 covers 10.0-10.127)
    addr = ipaddress.IPv4Address("10.128.0.0")
    assert trie.lookup(addr) == "AS8"

    # 11.0.0.0 is outside all our networks
    addr = ipaddress.IPv4Address("11.0.0.0")
    assert trie.lookup(addr) is None
