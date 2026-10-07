"""`d.rack` holds PLC modules flat; a harness holding one is an ERROR (model-0178, author-0031)."""

from typing import Any

import fransys as fr

from fransys_model.derive import item_designation
from fransys_model.vocab.tables import items

_DI = "DEMO-PLC-DI-2"
_CODE = "HARNESS_HOLDS_PLC_MODULE"


def _build(make: Any) -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.location("C1", "Cabinet")
    with d.function("PLC", "PLC"):
        container = make(d)
        d.device("DI1", _DI, name="di", parent=container, place="C1")
    return fr.build(d)


def _names(result: fr.BuildResult) -> dict[str, str]:
    return {
        i.tag: item_designation(result.model, i.id) for i in items(result.model).values() if i.tag
    }


def test_a_rack_container_keeps_its_modules_flat() -> None:
    """Can-fail: a rack that writes the harness mark prints the module `U1-DI1` and fails."""
    result = _build(lambda d: d.rack("U1", place="C1"))
    assert [f.code for f in result.findings if f.code == _CODE] == []
    assert _names(result)["DI1"] == "DI1"
    assert _names(result)["U1"] == "U1"


def test_a_harness_holding_a_plc_module_is_the_error_naming_d_rack() -> None:
    """Can-fail: dropping the check lets this build with no finding."""
    result = _build(lambda d: d.harness("U1", place="C1"))
    (found,) = [f for f in result.findings if f.code == _CODE]
    assert found.severity.name == "ERROR"
    assert "d.rack" in found.message
