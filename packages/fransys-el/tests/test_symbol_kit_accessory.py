"""`symbol_kit` gives no pick to a function of an accessory (ACCESSORY-UNDRAWN, ruling 25).

An untagged `parent=` device with `unused=True` is an accessory: it draws nothing. The holder
beside it draws as a box; a sibling device keeps its pick.
"""

import fransys as fr
from fransys.colours import BU
from fransys_el import symbol_kit
from placement_fixtures import leads

from electrical_symbols import LIBRARY
from fransys_model.vocab import functions, items

_FUSE = "DEMO-FUSE-HOLDER-PCB"


def _kit_keys() -> tuple[set[str], set[str]]:
    """(item keys that have a pick, item keys of every function) for a holder with two links."""
    d = fr.design("demo_parts")
    f1 = d.device("F1", _FUSE)
    holder = d.device("H2", "DEMO-LAMP-24")
    d.detail.wire(f1["1"], holder.lamp["1"], wire=(BU, 0.5))
    d.detail.wire(f1["2"], holder.lamp["2"], wire=(BU, 0.5))
    d.device(None, _FUSE, name="link-a", parent=holder, unused=True)
    d.device(None, _FUSE, name="link-b", parent=holder, unused=True)
    model = fr.build(d).model
    kit = symbol_kit(model, LIBRARY)
    by = {f.id: items(model)[f.item].key[-1] for f in functions(model).values()}
    return {by[f] for f in leads(kit)}, set(by.values())


def test_an_accessorys_functions_have_no_pick_while_a_sibling_has_one() -> None:
    picked, known = _kit_keys()
    assert {"link-a", "link-b"} <= known
    assert not picked & {"link-a", "link-b"}
    assert "F1" in picked  # H2 draws as a box, so the kit holds no pick for it
