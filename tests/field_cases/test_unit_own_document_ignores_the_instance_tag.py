"""Field case: an I/O board released as a unit, used alone and also as instance U3 beside an unrelated device in another design.
The bug (the risk the instance tag brings): the container's tag in a unit's own designations would change its listing, drawings and exports.
Fixed by model-0134, the unit's own document is unchanged byte for byte, and only the container prints the instance tag (-U3-J1)."""

from functools import cache
from typing import TYPE_CHECKING, Any

import fransys as fr
from _demo_board import demo_board

from fransys_model.vocab.tables import functions, items, ports

if TYPE_CHECKING:
    from pathlib import Path


_board = cache(demo_board)


def _build(tag: str, *, beside: bool) -> tuple[fr.BuildResult, Any]:
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    d.location("C2", "Other cabinet")
    board = d.add(_board(), tag)
    if beside:
        d.device("P1", "DEMO-CONN-2P", place="C2")
    return fr.build(d), board


def _own_texts(result: fr.BuildResult) -> list[tuple[Any, ...]]:
    """Every item and port text of the board unit's own document, keyed below the instance."""
    model = result.model
    unit = next(u for u in fr.derive.units(model) if fr.derive.unit_release(model, u).name == "demo-board")
    rows = [(item.key[1:], fr.derive.printed_designation(model, i, unit=unit)) for i, item in items(model).items() if item.unit == unit]
    rows += [
        (("port", p.name), fr.derive.port_designation(model, i, unit=unit))
        for i, p in ports(model).items()
        if items(model)[functions(model)[p.function].item].unit == unit
    ]
    return sorted(rows, key=repr)


def _own_exports(result: fr.BuildResult, out: Path) -> dict[str, bytes]:
    files = fr.write(result, out, unit="demo-board")
    return {f.name: f.read_bytes() for f in files}


def test_the_unit_own_texts_equal_the_standalone_build_while_the_container_prints_the_tag() -> None:
    alone, _ = _build("U1", beside=False)
    inside, board = _build("U3", beside=True)
    assert fr.derive.printed_designation(inside.model, board.J1.id) == "-U3-J1"
    assert _own_texts(inside) == _own_texts(alone)
    assert ("J1",) in {key[-1:] for key, _ in _own_texts(inside)}


def test_the_unit_own_exports_are_byte_identical_as_an_instance(tmp_path: Path) -> None:
    alone, _ = _build("U1", beside=False)
    inside, board = _build("U3", beside=True)
    assert fr.derive.printed_designation(inside.model, board.J1.id) == "-U3-J1"
    assert _own_exports(inside, tmp_path / "inside") == _own_exports(alone, tmp_path / "alone")
