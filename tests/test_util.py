import pytest
from types import SimpleNamespace

from kartograf import util
from kartograf.util import (
    KartografConfigurationError,
    parse_pfx,
    is_valid_pfx,
    get_root_network,
    rir_from_str,
)


def test_valid_ipv4_network():
    pfx = "192.144.11.0/24"
    assert parse_pfx(pfx) == pfx


def test_valid_ipv4_addr():
    pfx = "192.144.11.0"
    assert parse_pfx(pfx) == pfx


def test_valid_ipv6_network():
    pfx = "2001:db8::/64"
    assert parse_pfx(pfx) == pfx


def test_valid_ipv6_addr():
    pfx = "2001:db8::1"
    assert parse_pfx(pfx) == pfx


def test_invalid_ip_network():
    pfx = "192.1/asdf"
    assert parse_pfx(pfx) is None


def test_invalid_input():
    pfx = "no.slash"
    assert parse_pfx(pfx) is None


def test_invalid_prefixes():
    invalid_prefixes = [
        "not.a.prefix",
        "300.0.0.0/8",       # Invalid IPv4
        "2001:xyz::/32"      # Invalid IPv6
    ]
    for prefix in invalid_prefixes:
        assert is_valid_pfx(prefix) is False


def test_private_network():
    pfx = "0.128.0.0/24"
    assert parse_pfx(pfx) == pfx


def test_ipv4_prefix_with_leading_zeros():
    pfx = "010.10.00.00/16"
    assert parse_pfx(pfx) is None
    assert not is_valid_pfx(pfx)


def test_ipv6_prefix_with_leading_zeros():
    pfx = "001:db8::0/24"
    assert parse_pfx(pfx) is None
    assert not is_valid_pfx(pfx)


def test_get_root_network():
    ipv4 = "192.144.11.0/24"
    assert get_root_network(ipv4) == 192
    ipv6 = "2001:db8::/64"
    assert get_root_network(ipv6) == int("2001", 16)
    invalid = "not.a.network"
    assert get_root_network(invalid) is None


def test_rir_from_string():
    assert rir_from_str("ripe.db.route") == "RIPE"
    assert rir_from_str("ARIN-file") == "ARIN"
    assert rir_from_str("lacnic.db") == "LACNIC"
    assert rir_from_str("afrinic-data") == "AFRINIC"
    assert rir_from_str("apnic.db") == "APNIC"
    with pytest.raises(Exception):
        rir_from_str("invalid")


def test_check_compatibility_rejects_invalid_backend():
    with pytest.raises(KartografConfigurationError, match="Unknown RPKI backend"):
        util.check_compatibility("invalid")


def test_check_compatibility_threaded_requires_rpki_96(monkeypatch):
    monkeypatch.setattr(util, "get_rpki_local_version", lambda: "9.5")
    with pytest.raises(KartografConfigurationError, match="requires rpki-client version 9.6 or higher"):
        util.check_compatibility("threaded")


def test_check_compatibility_warns_when_legacy_on_96_plus(monkeypatch, capsys):
    monkeypatch.setattr(util, "get_rpki_local_version", lambda: "9.6")
    util.check_compatibility("legacy")

    captured = capsys.readouterr()
    assert "Notice: rpki-client 9.6+ detected" in captured.out


def test_get_rpki_local_version_parses_two_digit_minor(monkeypatch):
    def fake_run(*_args, **_kwargs):
        return SimpleNamespace(stderr="rpki-client-portable 9.10")

    monkeypatch.setattr(util.subprocess, "run", fake_run)

    assert util.get_rpki_local_version() == "9.10"


def test_check_compatibility_accepts_two_digit_minor(monkeypatch, capsys):
    monkeypatch.setattr(util, "get_rpki_local_version", lambda: "9.10")

    util.check_compatibility("threaded")

    captured = capsys.readouterr()
    assert "higher than 9.7" in captured.out


def test_get_rpki_thread_count_caps_to_eight(monkeypatch):
    monkeypatch.delenv("RPKI_MAX_THREADS", raising=False)
    monkeypatch.setattr(util.os, "cpu_count", lambda: 128)
    assert util.get_rpki_thread_count() == 8


def test_get_rpki_thread_count_uses_cpu_count(monkeypatch):
    monkeypatch.delenv("RPKI_MAX_THREADS", raising=False)
    monkeypatch.setattr(util.os, "cpu_count", lambda: 4)
    assert util.get_rpki_thread_count() == 4


def test_get_rpki_thread_count_falls_back_to_one(monkeypatch):
    monkeypatch.delenv("RPKI_MAX_THREADS", raising=False)
    monkeypatch.setattr(util.os, "cpu_count", lambda: None)
    assert util.get_rpki_thread_count() == 1


def test_get_rpki_thread_count_honors_env_cap(monkeypatch):
    monkeypatch.setenv("RPKI_MAX_THREADS", "3")
    monkeypatch.setattr(util.os, "cpu_count", lambda: 16)
    assert util.get_rpki_thread_count() == 3
