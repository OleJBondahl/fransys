"""Field case: every item-making call takes `external=` (device, terminal_strip, cable, harness).

The engineering shape: an upstream strip, cable or harness supplied by others. A device already
takes `external=True`; the other three item-making calls did not, so only a device could be
marked "by others" and the rest showed in the bill of materials.

The rule (EA15, G24): `external=True` flags the item. A strip's terminals are external through
the parent chain (spec Y1); a cable's conductors carry no flag (spec Y2); no item flagged
external reaches the bill of materials.
"""

import fransys as fr

from fransys_model.vocab.tables import items

_TERMINAL = "DEMO-TB-2.5"
_CABLE = "DEMO-CBL-4G1.5"
_LAMP = "DEMO-LAMP-24"


def _built(*, external: bool) -> fr.Model:
    """One device, strip, cable and harness, each made with `external=`."""
    d = fr.design("demo_parts", place="CAB")
    d.location("CAB", "Cabinet")
    d.device("H1", _LAMP, external=external)
    d.terminal_strip("X0", _TERMINAL, 2, external=external)
    d.cable("W0", _CABLE, external=external)
    d.harness("WH", external=external)
    return fr.build(d).model


def _flags(model: fr.Model) -> dict[str, bool]:
    """Item `tag` to its own `external` flag, for the tagged items."""
    return {i.tag: i.external for i in items(model).values() if i.tag}


def test_every_item_call_flags_its_item() -> None:
    """The four items carry the flag; the strip's terminals are external by the parent chain."""
    model = _built(external=True)
    assert _flags(model) == {"H1": True, "X0": True, "W0": True, "WH": True}
    strip = next(i for i in items(model).values() if i.tag == "X0")
    terminals = [i for i in items(model).values() if i.parent == strip.id]
    assert len(terminals) == 2
    assert all(fr.derive.external(model, t.id) and not t.external for t in terminals)


def test_external_items_leave_the_bom() -> None:
    """With the flag no flagged item has a BOM line; without it the strip's terminals do."""
    on, off = _built(external=True), _built(external=False)
    parts_on = {line.mpn for line in fr.derive.bom_lines(on)}
    parts_off = {line.mpn for line in fr.derive.bom_lines(off)}
    assert _TERMINAL not in parts_on
    assert _TERMINAL in parts_off
