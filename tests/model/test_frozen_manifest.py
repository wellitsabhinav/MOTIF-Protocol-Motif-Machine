import json
from pathlib import Path

import pytest

from tools.frozen_manifest import INITIAL, PROMOTED, compare, digest, inventory


def test_frozen_initial_inventory_is_model_and_subset_not_promoted_claim():
    data = json.loads(INITIAL.read_text())
    exchange = next(m for m in data["motifs"] if m["name"] == "BYTE_EXCHANGE")
    assert exchange["rtl_source"] is None
    assert exchange["protocol_users"] == ["i2c_target"]
    assert len(data["motifs"]) == 7
    assert data["firing_aliases"]["TURNAROUND"] == "BYTE_EXCHANGE"


def test_integrity_detects_added_removed_and_changed_hardware(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "motif").mkdir()
    (tmp_path / ".github/workflows").mkdir(parents=True)
    for name in ("info.yaml", "flow-lock.json", ".github/workflows/gds.yml", "src/motif.sv"):
        (tmp_path / name).write_text("original\n")
    baseline = inventory(tmp_path)
    (tmp_path / "src/escape.sv").write_text("new state\n")
    with pytest.raises(ValueError, match="added=.*escape"):
        compare(baseline, inventory(tmp_path))
    (tmp_path / "src/escape.sv").unlink()
    (tmp_path / "src/motif.sv").write_text("modified state\n")
    with pytest.raises(ValueError, match="changed=.*motif"):
        compare(baseline, inventory(tmp_path))
    (tmp_path / "src/motif.sv").unlink()
    with pytest.raises(ValueError, match="removed=.*motif"):
        compare(baseline, inventory(tmp_path))


def test_hash_ignores_only_platform_line_endings():
    assert digest(b"one\r\ntwo\r\n") == digest(b"one\ntwo\n")
    assert digest(b"one\ntwo\n") != digest(b"one\nother\n")


def test_promoted_boundary_if_present():
    if PROMOTED.exists():
        from tools.frozen_manifest import verify
        verify(PROMOTED, historical=True)


def test_physical_correspondence_cannot_hide_logic_or_extra_state():
    from tools.physical_correspondence import DECLARATION, declaration_correspondence
    old = "module m;\n" + DECLARATION + "assign out = a;\nendmodule\n"
    new = "module m;\nassign out = a;\n" + DECLARATION + "endmodule\n"
    declaration_correspondence(old, new)
    with pytest.raises(ValueError, match="exceeds"):
        declaration_correspondence(old, new.replace("= a", "= b"))
    with pytest.raises(ValueError, match="duplicated"):
        declaration_correspondence(old, new + DECLARATION)
