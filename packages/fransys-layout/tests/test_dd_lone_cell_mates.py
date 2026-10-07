"""EF-C2 part 1: `LONE_CELL` reads a pin's mate as wired (D5 for pins), built through the facade.

A device connector mated to a harness plug is drawn only as the pins whose plug pin is wired
(`_without_idle_pins`); such a pin view has no conductor of its own, so `LONE_CELL` must count
its mate's wire, as the pin-view filter does.
"""

from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import layout_trigger_document

from fransys_layout.lint.codes import LONE_CELL
from fransys_model.vocab.tables import functions, ports

_PROJECT: dict[str, Any] = {
    "title": "Lone cells",
    "number": "P-1005",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def _design():
    parts = fransys_parts.load("demo_parts")
    design = fransys_author.Design(parts)
    design.project(**_PROJECT)
    design.revision(1, date="2026-09-24", text="First issue", created="XX")
    return parts, design


def _lone_items(result) -> list[str]:
    """The key head of the item of every function or port that a `LONE_CELL` finding names."""
    model = result.model
    found = []
    for finding in result.findings:
        if finding.code != LONE_CELL:
            continue
        for subject in finding.subjects:
            function = ports(model)[subject].function if subject.kind == "port" else subject
            found.append(functions(model)[function].key[0])
    return found


def test_a_pin_wired_only_through_its_mate_is_no_lone_cell() -> None:
    """A harness plug's pin 2 is wired by a core; the device connector J0 it mates has no wire."""
    # UNDO: fransys_layout/lint/chains.py:_facts
    #     `unwired` ignores `mates` again (a pin view fires for having no conductor of its own)
    parts, d = _design()
    c1, grp = d.location("C1", "Cabinet"), d.group("A", "A")
    far, field = d.location("FLD", "Field"), d.group("F", "Field")
    harness = d.harness(name="w3", tag="W3", at=c1, group=field)
    plug = d.item("DEMO-CONN-2P", tag="P9", name="p9", parent=harness, at=c1, group=field)
    end = d.item("DEMO-CONN-2P", tag="PZ", name="pz", parent=harness, at=far, group=field)
    d.cable("DEMO-CBL-4G1.5", name="w3c", parent=harness, at=c1).core(1, plug["2"], end["2"])
    d.mate(plug, d.item("DEMO-CONN-2P", tag="J0", name="j0", at=c1, group=grp))
    assert "j0" not in _lone_items(fr.build(parts, d.draft(), layout_trigger_document()))


def _standalone_unit():
    """A demo unit whose boundary connector `X1` has no wire, and a lamp `H1` with none either."""
    parts, d = _design()
    unit = d.scope("cab", at=d.location("C1", "Cabinet")).unit(
        "demo-pump-cabinet", revision=2, interface="1"
    )
    unit.revision(2, date="2026-01-01", text="First release", created="XX")
    place = {"at": unit.location("C1", "Cab"), "group": unit.group("NET", "Net")}
    unit.boundary(unit.item("DEMO-CONN-2P", tag="X1", **place))
    unit.item("DEMO-LAMP-24", tag="H1", **place)
    return parts, d


def _lone_functions(result) -> list[tuple[str, ...]]:
    """The key of the function each `LONE_CELL` names, one entry per finding."""
    model = result.model
    found = []
    for finding in result.findings:
        if finding.code == LONE_CELL:
            subject = finding.subjects[0]
            function = ports(model)[subject].function if subject.kind == "port" else subject
            found.append(functions(model)[function].key)
    return found


def test_a_boundary_connector_is_open_on_its_own_set_and_an_unwired_symbol_still_fires() -> None:
    """G4: X1's outside is open by U2, so no `LONE_CELL` for it, in either drawing set it stands in.

    The unwired lamp inside the unit is the twin: it fires, exactly once. Before the fix X1 gave
    two findings per pin (its own set and the system set's stand-in).

    # UNDO: engines/schematic/engine.py, pass `open_ends=frozenset()` to `lint_chains`
    """
    parts, d = _standalone_unit()
    found = _lone_functions(fr.build(parts, d.draft(), layout_trigger_document()))
    assert found == [("cab", "H1", "fn", "lamp")]
