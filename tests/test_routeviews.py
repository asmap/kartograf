from pathlib import Path

from kartograf.collectors.routeviews import find_latest_pfx2as

# A verbatim copy of a CAIDA monthly directory listing
# (https://publicdata.caida.org/datasets/routing/routeviews-prefix2as/2026/08/)
LISTING_FIXTURE = Path(__file__).parent / "data" / "routeviews_listing.html"


def test_find_latest_pfx2as_real_listing():
    html = LISTING_FIXTURE.read_text()
    assert find_latest_pfx2as(html) == "routeviews-rv2-20260827-1200.pfx2as.gz"


def test_find_latest_pfx2as_ignores_other_links():
    html = (
        '<a href="../">Parent Directory</a>'
        '<a href="README.txt">README.txt</a>'
        '<a href="routeviews-rv2-20260101-1200.pfx2as.gz">first</a>'
        '<a href="routeviews-rv2-20260102-1200.pfx2as.gz">second</a>'
        '<a href="notes.md">notes</a>'
        '<a name="anchor-without-href">x</a>'
    )
    assert find_latest_pfx2as(html) == "routeviews-rv2-20260102-1200.pfx2as.gz"


def test_find_latest_pfx2as_no_match():
    assert find_latest_pfx2as('<html><body><a href="../">up</a></body></html>') == ""
