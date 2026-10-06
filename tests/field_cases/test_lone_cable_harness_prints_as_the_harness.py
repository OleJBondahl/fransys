"""Field case: a harness that holds one cable and no part of its own prints that cable as itself.

The engineering shape: a loom is drawn as a harness item (`-W1`) with two plugs (`-W1-J1`,
`-W1-J2`) and one cable between them. A reader names the loom and the cable by one text, "W1".

The bug: the cable printed behind its harness, `-W1-W1`, and its cores `-W1-W1:1`. Two cables in
one harness (`-W2-W1`, `-W2-W2`) and a harness with a part of its own (its BOM line also prints
`-W3`) keep the long form.

Raised by a consumer, 2026-10-06. Fixed by decision model-0148, which amends model-0043.
"""

from typing import TYPE_CHECKING

import fransys as fr
import pytest

from fransys_model.derive import bom_lines, cable_rows, printed_designation
from fransys_model.vocab.tables import items

if TYPE_CHECKING:
    from fransys_model.kernel import Model

_PLUG = "DEMO-CONN-2P"
_CABLE = "DEMO-CBL-4G1.5"
_DUPLICATE = "DESIGNATION_DUPLICATE"


def _loom(d: fr.Design, tag: str, cables: tuple[str, ...], *, part: str | None = None) -> None:
    """Harness `tag` with plugs J1 and J2 and one cable per tag in `cables`, a core on each."""
    with d.function(tag, f"Loom {tag}"):
        loom = d.device(tag, part, place="L0") if part else d.harness(tag, place="L0")
        near = d.device("J1", _PLUG, parent=loom, place="L0")
        far = d.device("J2", _PLUG, parent=loom, place="L0")
        for cable_tag in cables:
            d.cable(cable_tag, _CABLE, parent=loom, name=f"cable{cable_tag}", place="L0").core(
                1, near[1], far[1]
            )


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    """Three looms: W1 with one cable, W2 with two, W3 with its own part and one cable."""
    d = fr.design("demo_parts")
    d.location("L0", "Workshop")
    _loom(d, "W1", ("W1",))
    _loom(d, "W2", ("W1", "W2"))
    _loom(d, "W3", ("W1",), part=_PLUG)
    return fr.build(d)


def _printed(model: Model) -> dict[str, str]:
    """Every item's printed designation by its key text, `"W1/cableW1"` the cable of loom W1."""
    return {
        "/".join(item.key): printed_designation(model, id_) for id_, item in items(model).items()
    }


def test_the_lone_cable_prints_as_its_harness(built: fr.BuildResult) -> None:
    """Loom W1: the cable is `-W1`, its plugs `-W1-J1` and `-W1-J2`."""
    printed = _printed(built.model)
    assert printed["W1/cableW1"] == "-W1"
    assert printed["W1/J1"] == "-W1-J1"
    assert printed["W1/J2"] == "-W1-J2"


def test_the_lone_cables_cores_follow(built: fr.BuildResult) -> None:
    """The core rows name the cable `-W1`, never `-W1-W1`."""
    model = built.model
    (cable,) = [id_ for id_, item in items(model).items() if "/".join(item.key) == "W1/cableW1"]
    assert {row.cable_designation for row in cable_rows(model, cable)} == {"-W1"}


def test_two_cables_and_an_own_part_keep_the_long_form(built: fr.BuildResult) -> None:
    """Loom W2 prints -W2-W1 and -W2-W2; loom W3, with a part, prints -W3-W1, itself -W3."""
    printed = _printed(built.model)
    assert printed["W2/cableW1"] == "-W2-W1"
    assert printed["W2/cableW2"] == "-W2-W2"
    assert printed["W3/cableW1"] == "-W3-W1"
    assert printed["W3/W3"] == "-W3"


def test_bom_rows_and_no_duplicate(built: fr.BuildResult) -> None:
    """The BOM prints each designation once: `-W1` for the lone cable, `-W3` for the own part."""
    lines = {line.mpn: line.designations for line in bom_lines(built.model)}
    assert "-W1" in lines[_CABLE]
    assert "-W1-W1" not in lines[_CABLE]
    assert "-W2-W1" in lines[_CABLE]
    assert "-W3" in lines[_PLUG]
    assert not [f for f in built.findings if "DUPLICATE" in f.code]
