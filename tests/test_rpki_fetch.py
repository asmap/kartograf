import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from kartograf.rpki.fetch import validate_rpki_db
from kartograf.util import KartografConfigurationError, calculate_sha256


def _create_context(tmp_path, backend):
    cache = tmp_path / f"cache_{backend}"
    tals = tmp_path / f"tals_{backend}"
    out = tmp_path / f"out_{backend}"

    cache.mkdir(parents=True, exist_ok=True)
    tals.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)

    # The legacy flow validates discovered .roa files with -f batches.
    (cache / "sample.roa").write_text("dummy", encoding="utf-8")

    # data_tals() requires all five TAL files to be present.
    for tal in ["afrinic", "apnic", "arin", "lacnic", "ripe"]:
        (tals / f"{tal}.tal").write_text("tal", encoding="utf-8")

    return SimpleNamespace(
        rpki_backend=backend,
        data_dir_rpki_cache=str(cache),
        data_dir_rpki_tals=str(tals),
        out_dir_rpki=str(out),
        epoch="111111114",
        debug_log=None,
        cleanup_out_files=[],
    )


def test_validate_rpki_db_legacy_threaded_parity(tmp_path, monkeypatch):
    legacy_context = _create_context(tmp_path, "legacy")
    threaded_context = _create_context(tmp_path, "threaded")

    legacy_roa = (
        b'{"type":"roa","validation":"OK","valid_until":200,'
        b'"vrps":[{"prefix":"101.0.1.0/24","asid":11102,"maxlen":24}]}'
    )
    threaded_payload = {
        "roas": [
            {
                "prefix": "101.0.1.0/24",
                "asn": 11102,
                "maxLength": 24,
                "ta": "arin",
                "expires": 200,
            }
        ]
    }

    def fake_run_legacy(cmd, check=False, **_kwargs):
        assert "-f" in cmd
        assert check is False
        return SimpleNamespace(stdout=legacy_roa, stderr=b"", returncode=0)

    monkeypatch.setattr("kartograf.rpki.fetch.subprocess.run", fake_run_legacy)
    validate_rpki_db(legacy_context)

    legacy_raw = Path(legacy_context.out_dir_rpki) / "rpki_raw.json"
    legacy_hash = calculate_sha256(legacy_raw)

    def fake_run_threaded(cmd, stdout=None, stderr=None, check=False, text=False, **_kwargs):
        assert "-p" in cmd
        assert stdout is not None
        assert stderr is not None
        assert check is False
        assert text is True
        json.dump(threaded_payload, stdout)
        return SimpleNamespace(stdout="", stderr="", returncode=0)

    monkeypatch.setattr("kartograf.rpki.fetch.subprocess.run", fake_run_threaded)
    validate_rpki_db(threaded_context)

    threaded_raw = Path(threaded_context.out_dir_rpki) / "rpki_raw.json"
    threaded_hash = calculate_sha256(threaded_raw)

    with open(legacy_raw, "r", encoding="utf-8") as f_legacy:
        legacy_data = json.load(f_legacy)
    with open(threaded_raw, "r", encoding="utf-8") as f_threaded:
        threaded_data = json.load(f_threaded)

    assert legacy_data == threaded_data
    assert legacy_hash == threaded_hash


def test_validate_rpki_db_threaded_uses_bounded_workers(tmp_path, monkeypatch):
    context = _create_context(tmp_path, "threaded")
    commands = []

    # Even very large CPU counts should be clamped by get_rpki_thread_count().
    monkeypatch.setattr("kartograf.util.os.cpu_count", lambda: 128)

    def fake_run_threaded(cmd, stdout=None, stderr=None, check=False, text=False, **_kwargs):
        commands.append(cmd)
        json.dump({"roas": []}, stdout)
        return SimpleNamespace(stdout="", stderr="", returncode=0)

    monkeypatch.setattr("kartograf.rpki.fetch.subprocess.run", fake_run_threaded)
    validate_rpki_db(context)

    assert commands, "Expected rpki-client to be executed"
    cmd = commands[0]
    assert "-p" in cmd
    thread_flag_index = cmd.index("-p")
    assert cmd[thread_flag_index + 1] == "8"


def test_validate_rpki_db_legacy_raises_on_subprocess_error(tmp_path, monkeypatch):
    context = _create_context(tmp_path, "legacy")

    def fake_run_legacy(_cmd, **_kwargs):
        return SimpleNamespace(stdout=b"", stderr=b"error", returncode=1)

    monkeypatch.setattr("kartograf.rpki.fetch.subprocess.run", fake_run_legacy)

    with pytest.raises(KartografConfigurationError, match="legacy validation failed"):
        validate_rpki_db(context)


def test_validate_rpki_db_threaded_raises_on_subprocess_error(tmp_path, monkeypatch):
    context = _create_context(tmp_path, "threaded")

    def fake_run_threaded(_cmd, stdout=None, **_kwargs):
        json.dump({"roas": []}, stdout)
        return SimpleNamespace(stdout="", stderr="error", returncode=2)

    monkeypatch.setattr("kartograf.rpki.fetch.subprocess.run", fake_run_threaded)

    with pytest.raises(KartografConfigurationError, match="threaded validation failed"):
        validate_rpki_db(context)


def test_validate_rpki_db_legacy_raises_on_malformed_batch_output(tmp_path, monkeypatch):
    context = _create_context(tmp_path, "legacy")

    def fake_run_legacy(_cmd, **_kwargs):
        return SimpleNamespace(stdout=b'{"type":"roa"', stderr=b"", returncode=0)

    monkeypatch.setattr("kartograf.rpki.fetch.subprocess.run", fake_run_legacy)

    with pytest.raises(KartografConfigurationError, match="malformed concatenated JSON output"):
        validate_rpki_db(context)


def test_validate_rpki_db_legacy_raises_on_timeout(tmp_path, monkeypatch):
    context = _create_context(tmp_path, "legacy")

    def fake_run_legacy(_cmd, **_kwargs):
        raise subprocess.TimeoutExpired(cmd="rpki-client", timeout=1)

    monkeypatch.setattr("kartograf.rpki.fetch.subprocess.run", fake_run_legacy)

    with pytest.raises(KartografConfigurationError, match="legacy validation timed out"):
        validate_rpki_db(context)


def test_validate_rpki_db_threaded_raises_on_timeout(tmp_path, monkeypatch):
    context = _create_context(tmp_path, "threaded")

    def fake_run_threaded(_cmd, **_kwargs):
        raise subprocess.TimeoutExpired(cmd="rpki-client", timeout=1)

    monkeypatch.setattr("kartograf.rpki.fetch.subprocess.run", fake_run_threaded)

    with pytest.raises(KartografConfigurationError, match="threaded validation timed out"):
        validate_rpki_db(context)


@pytest.mark.parametrize("backend", ["", "future"])
def test_validate_rpki_db_rejects_unknown_backend(tmp_path, backend):
    context = _create_context(tmp_path, backend)

    with pytest.raises(KartografConfigurationError, match="Unsupported RPKI backend"):
        validate_rpki_db(context)
