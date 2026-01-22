import copy
import ipaddress
import random
from kartograf.asmap import ASMap, ASNEntry, net_to_prefix, prefix_to_net


def test_ipv6_prefix_roundtrips() -> None:
    """Test that random IPv6 network ranges roundtrip through prefix encoding."""
    for _ in range(20):
        net_bits = random.getrandbits(128)
        for prefix_len in range(0, 129):
            masked_bits = (net_bits >> (128 - prefix_len)) << (128 - prefix_len)
            net = ipaddress.IPv6Network((masked_bits.to_bytes(16, 'big'), prefix_len))
            prefix = net_to_prefix(net)
            assert len(prefix) <= 128
            net2 = prefix_to_net(prefix)
            assert net == net2

def test_ipv4_prefix_roundtrips() -> None:
    """Test that random IPv4 network ranges roundtrip through prefix encoding."""
    for _ in range(100):
        net_bits = random.getrandbits(32)
        for prefix_len in range(0, 33):
            masked_bits = (net_bits >> (32 - prefix_len)) << (32 - prefix_len)
            net = ipaddress.IPv4Network((masked_bits.to_bytes(4, 'big'), prefix_len))
            prefix = net_to_prefix(net)
            assert 32 <= len(prefix) <= 128
            net2 = prefix_to_net(prefix)
            assert net == net2

def test_asmap_roundtrips() -> None:
    """Test case that verifies random ASMap objects roundtrip to/from entries/binary."""
    # Iterate over the number of leaves the random test ASMap objects have.
    for leaves in range(1, 10):
        # Iterate over the number of bits in the AS numbers used.
        for asnbits in range(0, 10):
            # Iterate over the probability that leaves are unassigned.
            for pct in range(101):
                # Construct a random ASMap object according to the above parameters.
                asmap = ASMap.from_random(num_leaves=leaves, max_asn=1 + (1 << asnbits),
                                          unassigned_prob=0.01 * pct)
                # Run tests for to_entries and construction from those entries, both
                # for overlapping and non-overlapping ones.
                for overlapping in [False, True]:
                    entries = asmap.to_entries(overlapping=overlapping, fill=False)
                    random.shuffle(entries)
                    asmap2 = ASMap(entries)
                    assert asmap2 is not None
                    assert asmap2 == asmap
                    entries = asmap.to_entries(overlapping=overlapping, fill=True)
                    random.shuffle(entries)
                    asmap2 = ASMap(entries)
                    assert asmap2 is not None
                    assert asmap2.extends(asmap)

                # Run tests for to_binary and construction from binary.
                enc = asmap.to_binary(fill=False)
                asmap3 = ASMap.from_binary(enc)
                assert asmap3 is not None
                assert asmap3 == asmap
                enc = asmap.to_binary(fill=True)
                asmap3 = ASMap.from_binary(enc)
                assert asmap3 is not None
                assert asmap3.extends(asmap)

def test_patching() -> None:
    """Test behavior of update, lookup, extends, and diff."""
    #pylint: disable=too-many-locals,too-many-nested-blocks
    # Iterate over the number of leaves the random test ASMap objects have.
    for leaves in range(1, 10):
        # Iterate over the number of bits in the AS numbers used.
        for asnbits in range(0, 10):
            # Iterate over the probability that leaves are unassigned.
            for pct in range(0, 101):
                # Construct a random ASMap object according to the above parameters.
                asmap = ASMap.from_random(num_leaves=leaves, max_asn=1 + (1 << asnbits),
                                          unassigned_prob=0.01 * pct)
                # Make a copy of that asmap object to which patches will be applied.
                # It starts off being equal to asmap.
                patched = copy.copy(asmap)
                # Keep a list of patches performed.
                patches: list[ASNEntry] = []
                # Initially there cannot be any difference.
                assert not asmap.diff(patched)
                # Make 5 patches, each building on top of the previous ones.
                for _ in range(0, 5):
                    # Construct a random path and new ASN to assign it to, apply it to patched,
                    # and remember it in patches.
                    pathlen = random.randrange(5)
                    path = [random.getrandbits(1) != 0 for _ in range(pathlen)]
                    newasn = random.randrange(1 + (1 << asnbits))
                    patched.update(path, newasn)
                    patches = [(path, newasn)] + patches

                    # Compute the diff, and whether asmap extends patched, and the other way
                    # around.
                    diff = asmap.diff(patched)
                    assert(asmap == patched) == (len(diff) == 0)
                    extends = asmap.extends(patched)
                    back_extends = patched.extends(asmap)
                    # Determine whether those extends results are consistent with the diff
                    # result.
                    assert extends == (all(d[2] == 0 for d in diff))
                    assert back_extends == (all(d[1] == 0 for d in diff))
                    # For every diff found:
                    for path, old_asn, new_asn in diff:
                        # Verify asmap and patched actually differ there.
                        assert old_asn != new_asn
                        assert asmap.lookup(path) == old_asn
                        assert patched.lookup(path) == new_asn
                        for _ in range(2):
                            # Extend the path far enough that it's smaller than any mapped
                            # range, and check the lookup holds there too.
                            spec_path = list(path)
                            while len(spec_path) < 32:
                                spec_path.append(random.getrandbits(1) != 0)
                            assert asmap.lookup(spec_path) == old_asn
                            assert patched.lookup(spec_path) == new_asn
                            # Search through the list of performed patches to find the last one
                            # applying to the extended path (note that patches is in reverse
                            # order, so the first match should work).
                            found = False
                            for patch_path, patch_asn in patches:
                                if spec_path[:len(patch_path)] == patch_path:
                                    # When found, it must match whatever the result was patched
                                    # to.
                                    assert new_asn == patch_asn
                                    found = True
                                    break
                            # And such a patch must exist.
                            assert found
