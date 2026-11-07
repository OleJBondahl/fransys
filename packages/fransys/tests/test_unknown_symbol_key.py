"""A symbol key a part file names that the library lacks is an ERROR from el (R242, el-0039); a wrong symbol for a part's ports likewise.

The function is the subject, its page is read from the layout, and it is drawn as a generic box.
"""
# UNPRINTED_SET was invalid test input: the devices stand in the printed cabinet (FIXTURE-VALID).

import shutil
from pathlib import Path

import demo_parts
import fransys as fr
import pytest
from _expected_codes import expect_codes
from _model_build_cover import cabinet_document
from fransys import BuildFailedError, Severity

_KEY = "no-such-symbol"


def _built(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, symbol: str | None) -> fr.BuildResult:
    """One relay whose part file names `symbol` for its coil, in a copy of the demo library."""
    library = "demo_parts" if symbol is None else f"bad_{symbol.replace('-', '_')}_parts"  # one import name per symbol: imports are cached
    if symbol is not None:
        shutil.copytree(Path(demo_parts.__file__).parent, tmp_path / library, ignore=shutil.ignore_patterns("__pycache__"))
        part = tmp_path / library / "parts" / "relay-2co-24vdc.toml"
        part.write_text(part.read_text(encoding="utf-8").replace('symbol = "operating-device"', f'symbol = "{symbol}"', 1), encoding="utf-8")
        monkeypatch.syspath_prepend(str(tmp_path))
    d = fr.design(library)
    cabinet = d.location("C1", "Cabinet")
    k1 = d.device("K1", "DEMO-RLY-2CO-24", place="C1")
    g1 = d.device("G1", "DEMO-PSU-24", place="C1")
    d.ac_supply("MAINS", 230, g1.input["L"], n=g1.input["N"])
    dc = d.dc_supply("24VDC", g1)
    with d.function("FIELD", "Feed"):
        d.series(dc.plus, k1.coil, dc.minus, wire=("BU", 0.75))
    return fr.build(d, cabinet_document(cabinet))


def test_an_unknown_key_is_one_error_naming_the_function_and_its_page(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result = _built(tmp_path, monkeypatch, _KEY)
    expect_codes(result, "UNKNOWN_SYMBOL_KEY")
    (found,) = (f for f in result.findings if f.code == "UNKNOWN_SYMBOL_KEY")
    assert found.severity is Severity.ERROR
    assert len(found.subjects) == 1
    assert found.message.startswith(f"symbol {_KEY!r} is not in the library (p2")
    assert found.message.endswith(": K1:coil)")
    assert found.fix
    keys = [s.key for page in result.drawings.values() for s in page.symbols]
    assert "generic-box" in keys


def test_a_known_key_gives_no_such_finding(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result = _built(tmp_path, monkeypatch, None)
    assert not [f for f in result.findings if f.code == "UNKNOWN_SYMBOL_KEY"]


def test_write_refuses_an_unknown_key_and_writes_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out_dir = tmp_path / "out"
    result = _built(tmp_path, monkeypatch, _KEY)
    expect_codes(result, "UNKNOWN_SYMBOL_KEY")
    with pytest.raises(BuildFailedError):
        fr.write(result, out_dir)
    assert not out_dir.exists() or list(out_dir.iterdir()) == []


def test_a_symbol_whose_ports_the_part_lacks_is_a_symbol_port_missing_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result = _built(tmp_path, monkeypatch, "psu")
    expect_codes(result, "SYMBOL_PORT_MISSING")
    (found,) = (f for f in result.findings if f.code == "SYMBOL_PORT_MISSING")
    assert found.severity is Severity.ERROR
    assert "part 'DEMO-RLY-2CO-24'" in found.message
    assert "symbol 'psu'" in found.message
    with pytest.raises(BuildFailedError):
        fr.write(result, tmp_path / "out")
