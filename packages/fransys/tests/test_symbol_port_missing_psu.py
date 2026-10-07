"""A wrong symbol chosen for a demo relay is a `SYMBOL_PORT_MISSING` finding, never a `KeyError`.

`d.symbol(<relay or one of its functions>, "psu")` gives the relay a five-port symbol that none
of its ports match: an authoring error, so it must come out of `fr.build` as the facade's
`SYMBOL_PORT_MISSING` `ERROR` (decision 0018) and make `fr.write` raise `BuildErrors`.

Choosing the symbol for the whole item (all three functions, one symbol) draws the item as one
view (`fransys_layout`'s `_item_views`), so the `SymbolPortError` then names the item, not a
function: that case used to raise a bare `KeyError` from `_symbol_port_missing_finding`.
"""

import fransys as fr
import fransys_author
import pytest
from _model_build_cover import cabinet_document
from fransys import BuildErrors, BuildResult, Severity


def _relay_with_the_wrong_symbol(*, whole_item: bool) -> BuildResult:
    parts = fr.parts("demo_parts")
    d = fransys_author.Design(parts)
    d.project(
        title="Demo",
        number="DEMO-PSU",
        customer="Demo Co",
        revision=1,
        author="demo",
    )
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    c1 = d.location("C1", "Demo cabinet")
    sup = d.group("SUP", "Supply")
    k1 = d.item("DEMO-RLY-2CO-24", tag="K1", at=c1, group=sup)
    d.symbol(k1 if whole_item else k1.fn("coil"), "psu")
    return fr.build(parts, d.draft(), cabinet_document(c1))


@pytest.mark.parametrize("whole_item", [False, True], ids=["one-function", "whole-item"])
def test_a_wrong_symbol_is_a_symbol_port_missing_finding(tmp_path, whole_item):
    """`fr.build` gives one `SYMBOL_PORT_MISSING` `ERROR`; `fr.write` raises and writes nothing."""
    result = _relay_with_the_wrong_symbol(whole_item=whole_item)

    raw = [f for f in result.findings if f.code == "SYMBOL_PORT_MISSING"]
    assert len(raw) == 1
    assert raw[0].severity is Severity.ERROR
    assert "part 'DEMO-RLY-2CO-24'" in raw[0].message
    assert "symbol 'psu'" in raw[0].message

    out_dir = tmp_path / "out"
    with pytest.raises(BuildErrors) as excinfo:
        fr.write(result, out_dir)
    assert any(f.code == "SYMBOL_PORT_MISSING" for f in excinfo.value.findings)
    assert not out_dir.exists() or list(out_dir.iterdir()) == []
