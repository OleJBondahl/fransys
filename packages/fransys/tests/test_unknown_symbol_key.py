"""An authored symbol key the library lacks is one UNKNOWN_SYMBOL_KEY ERROR from el (R242, el-0039).

The function is the subject, its page is read from the layout, and it is drawn as a generic box.
"""

lazy from pathlib import Path

import fransys as fr
import pytest
from _model_build_cover import cabinet_document
from fransys import BuildErrors, Severity

_KEY = "no-such-symbol"


def _built(key: str | None) -> fr.BuildResult:
    d = fr.design("demo_parts")
    cabinet = d.location("C1", "Cabinet")
    k1 = d.device("K1", "DEMO-RLY-2CO-24")
    k2 = d.device("K2", "DEMO-RLY-2CO-24")
    with d.function("FIELD", "Feed"):
        d.series(k1.coil, k2.coil, wire=("BU", 0.75))
    if key is not None:
        d.layout.symbol(k1.coil, key)
    return fr.build(d, cabinet_document(cabinet))


def test_an_unknown_key_is_one_error_naming_the_function_and_its_page() -> None:
    result = _built(_KEY)
    (found,) = (f for f in result.findings if f.code == "UNKNOWN_SYMBOL_KEY")
    assert found.severity is Severity.ERROR
    assert len(found.subjects) == 1
    assert found.message.startswith(f"symbol {_KEY!r} is not in the library (p1")
    assert found.message.endswith(": K1:coil)")
    assert found.fix
    keys = [s.key for page in result.drawings.values() for s in page.symbols]
    assert "generic-box" in keys


def test_a_known_key_gives_no_such_finding() -> None:
    result = _built(None)
    assert not [f for f in result.findings if f.code == "UNKNOWN_SYMBOL_KEY"]


def test_write_refuses_an_unknown_key_and_writes_nothing(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    with pytest.raises(BuildErrors) as excinfo:
        fr.write(_built(_KEY), out_dir)
    assert any(f.code == "UNKNOWN_SYMBOL_KEY" for f in excinfo.value.findings)
    assert not out_dir.exists() or list(out_dir.iterdir()) == []
