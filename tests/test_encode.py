import hashlib
import ipaddress
from pathlib import Path

import pytest

from kartograf.cli import create_parser
from kartograf.kartograf import Kartograf
from kartograf.vendor.bitcoin_core.asmap import ASMap, net_to_prefix


EPOCH = "1700000000"
INPUT_MAP = (
    "2001:db8:1::/48 AS4\n"
    "10.0.0.0/24 AS2\n"
    "10.0.0.0/23 AS1\n"
    "2001:db8::/32 AS3\n"
)
FINAL_MAP = (
    "10.0.0.0/24 AS2\n"
    "10.0.0.0/23 AS1\n"
    "2001:db8::/32 AS3\n"
    "2001:db8:1::/48 AS4\n"
)


@pytest.fixture(name="map_run")
def fixture_map_run(tmp_path, monkeypatch):
    """Run the real sorting, encoding, cleanup and reporting without fetching."""
    work_dir = tmp_path / "run with spaces"
    work_dir.mkdir()
    monkeypatch.chdir(work_dir)
    monkeypatch.setattr("kartograf.context.time.time", lambda: int(EPOCH))
    monkeypatch.setattr("kartograf.kartograf.check_compatibility", lambda: None)
    monkeypatch.setattr("kartograf.kartograf.fetch_rpki_db", lambda context: None)
    monkeypatch.setattr("kartograf.kartograf.validate_rpki_db", lambda context: None)
    monkeypatch.setattr("kartograf.kartograf.wait_for_launch", lambda epoch: None)

    def parse_rpki(context):
        input_file = Path(context.out_dir_rpki) / "rpki_final.txt"
        input_file.write_text(INPUT_MAP)
        context.cleanup_out_files.append(input_file)

    monkeypatch.setattr("kartograf.kartograf.parse_rpki", parse_rpki)
    return work_dir


@pytest.mark.parametrize("mode,options", [
    ("fresh", []),
    ("fresh", ["--encode", "--wipe_data_dir"]),
    ("reproduce", ["--encode", "--debug"]),
    ("wait", ["-e"]),
])
def test_map_encodings(map_run, mode, options, capsys):
    arguments = ["map", *options]
    if mode == "reproduce":
        data_dir = map_run / "original data"
        data_dir.mkdir()
        arguments.extend(["-r", str(data_dir), "-t", EPOCH])
    else:
        data_dir = map_run / "data" / EPOCH
        if mode == "wait":
            arguments.extend(["--wait", EPOCH])

    args = create_parser().parse_args(arguments)
    Kartograf.map(args)

    output = capsys.readouterr().out
    out_dir = map_run / "out" / (f"r{EPOCH}" if mode == "reproduce" else EPOCH)
    text_result = out_dir / "final_result.txt"
    assert text_result.read_text() == FINAL_MAP
    text_hash = hashlib.sha256(text_result.read_bytes()).hexdigest()
    assert f"The SHA-256 hash of the result file is: {text_hash}" in output
    assert data_dir.exists() is (not args.wipe_data_dir)
    assert (out_dir / "rpki" / "rpki_final.txt").exists() is args.debug

    if not args.encode:
        assert not list(out_dir.glob("*.dat"))
        assert "Encoding results" not in output
        return

    assert {path.name for path in out_dir.glob("*.dat")} == {
        f"{EPOCH}_asmap.dat", f"{EPOCH}_asmap_unfilled.dat",
    }
    assert output.index("Sorting results") < output.index("Encoding results")
    assert output.index("Encoding results") < output.index("Finishing Kartograf")

    for suffix in ("", "_unfilled"):
        binary_file = out_dir / f"{EPOCH}_asmap{suffix}.dat"
        contents = binary_file.read_bytes()
        file_hash = hashlib.sha256(contents).hexdigest()
        assert f"The SHA-256 hash of {binary_file.name} is: {file_hash}" in output
        decoded = ASMap.from_binary(contents)
        assert decoded is not None
        for address, asn in [
            ("10.0.0.1", 2), ("10.0.1.1", 1),
            ("2001:db8::1", 3), ("2001:db8:1::1", 4),
        ]:
            assert decoded.lookup(net_to_prefix(ipaddress.ip_network(address))) == asn
        unassigned = decoded.lookup(net_to_prefix(ipaddress.ip_network("10.0.2.1")))
        if suffix == "_unfilled":
            assert unassigned == 0
        else:
            assert unassigned > 0


def test_encoding_failure_preserves_data(map_run, monkeypatch, capsys):
    """An out-of-range ASN must fail the run before cleanup or success reporting."""
    def parse_rpki(context):
        (Path(context.out_dir_rpki) / "rpki_final.txt").write_text("10.0.0.0/8 AS33521665\n")

    monkeypatch.setattr("kartograf.kartograf.parse_rpki", parse_rpki)
    args = create_parser().parse_args(["map", "--encode", "--max_encode", "0", "--wipe_data_dir"])
    with pytest.raises(SystemExit, match=f"Failed to encode {EPOCH}_asmap.dat"):
        Kartograf.map(args)

    out_dir = map_run / "out" / EPOCH
    assert (out_dir / "final_result.txt").exists()
    assert (map_run / "data" / EPOCH).exists()
    assert not list(out_dir.glob("*.dat"))
    output = capsys.readouterr().out
    assert "Finishing Kartograf" not in output
    assert "The SHA-256 hash" not in output
