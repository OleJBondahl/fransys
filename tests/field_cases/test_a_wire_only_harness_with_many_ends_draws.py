"""Field case: a harness of plain wires with several far ends is drawn on its harness drawing.

The engineering shape: a harness W1 of plain wires (no cable). One plug is mated to a header;
its pins run to other plugs or headers.
(a) A 10-pin plug whose pins 1-4, 5-8 and 9-10 go to plugs on 4-, 4- and 2-pin headers.
(b) A 14-pin plug whose pins fan out to three 2-pin headers' own pins (no plug there),
    alternating: (3, 10), (4, 11), (5, 12).

The bug: the HARNESS_DRAWING document stops with DOCUMENT_NO_DRAWINGS, "missing drawing for"
W1, and writes nothing. The same harness with three ends (a) or with the far pins in order (b)
draws. Diagnosis: HARNESS-ENDS-1. Fixed by layout-0163: the retry plans again at its own origin.

The drawn order: a wire's core key ran as a plain string, so pin 10 sorted before pin 2 and the
plugs came out J2, J4, J3. Fixed by model-0185: the key is the natural order of the printed ends.
"""

from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
import fransys_parts
from fransys.colours import WH

from fransys_model.derive.cable_drawing import drawn_pins, end_rows
from fransys_model.kernel import Severity, merge

if TYPE_CHECKING:
    from pathlib import Path


def _part(mpn: str, pins: int, gender: str) -> str:
    ports = ", ".join(f'{{ name = "{n}", role = "generic" }}' for n in range(1, pins + 1))
    return (
        f'schema = 1\n[part]\nmpn = "{mpn}"\nmanufacturer = "Demo"\ndescription = "{mpn}"\n'
        'category = "connector"\nclass_code = "X"\n[[function]]\nname = "x"\nkind = "connector"\n'
        f'ports = [{ports}]\n[function.connector]\nstyle = "c-{pins}p"\npincount = {pins}\n'
        f'gender = "{gender}"\n'
    )


def _device_part(mpn: str, sizes: tuple[int, ...]) -> str:
    """One device with a male connector function per size, ports "1".."n"."""
    text = f'schema = 1\n[part]\nmpn = "{mpn}"\nmanufacturer = "Demo"\ndescription = "{mpn}"\n'
    text += 'category = "generic"\nclass_code = "U"\n'
    for k, pins in enumerate(sizes, start=1):
        ports = ", ".join(f'{{ name = "{n}", role = "generic" }}' for n in range(1, pins + 1))
        text += f'[[function]]\nname = "x{k}"\nkind = "connector"\nports = [{ports}]\n'
        text += f'[function.connector]\nstyle = "c-{pins}p"\npincount = {pins}\ngender = "male"\n'
    return text


def _design(tmp_path: Path) -> fr.Design:
    (tmp_path / "library.toml").write_text(
        'schema = 1\nname = "t"\nversion = "0.0.0"\ndescription = "d"\n', encoding="utf-8"
    )
    (tmp_path / "parts").mkdir()
    for pins in (2, 4, 6, 10, 14, 16):
        for kind, gender in (("PLG", "female"), ("HDR", "male")):
            text = _part(f"T-{kind}-{pins}", pins, gender)
            (tmp_path / "parts" / f"{kind}-{pins}.toml").write_text(text, encoding="utf-8")
    text = _device_part("T-QUAD", (16, 4, 10, 6))
    (tmp_path / "parts" / "quad.toml").write_text(text, encoding="utf-8")
    draft = merge(fransys_parts.load("demo_parts"), fransys_parts.load_path(tmp_path))
    return fr.Design(draft, place="C1")


def _built(d: fr.Design, w1: Any, cover: Path) -> fr.BuildResult:
    cover.write_text("# Harness\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.HARNESS_DRAWING, w1, cover=cover))


def _drawn(d: fr.Design, w1: Any, cover: Path) -> list[str]:
    built = _built(d, w1, cover)
    return [f"{f.code}" for f in fr.check(built) if f.severity is Severity.ERROR]


def _order(
    d: fr.Design, w1: Any, cover: Path, tags: dict[str, Any]
) -> tuple[list[str], list[str], dict[str, list[str]]]:
    """The tags of the top and bottom ends, and every end's pin markings, in drawing order (CD6)."""
    model = _built(d, w1, cover).model
    by_id = {dev.id: tag for tag, dev in tags.items()}
    top, bottom = end_rows(model, w1.id, None)
    pins = {
        tag: [p.marking for p in drawn_pins(model, w1.id, dev.id, None)]
        for tag, dev in tags.items()
    }
    return [by_id[i] for i in top], [by_id[i] for i in bottom], pins


def _plug(d: fr.Design, w1: Any, tag: str, pins: int, header: str) -> Any:
    plug = d.device(tag, f"T-PLG-{pins}", parent=w1)
    d.mate(plug, d.device(header, f"T-HDR-{pins}"))
    return plug


def test_a_plug_to_three_plugs_of_plain_wires_draws(tmp_path: Path) -> None:
    """(a) One 10-pin plug to 4-, 4- and 2-pin plugs: no ERROR, so the one block is drawn."""
    d = _design(tmp_path)
    d.location("C1", "Cabinet")
    w1 = d.harness("W1", place="C1")
    j1 = _plug(d, w1, "J1", 10, "X1")
    tags = {"J1": j1}
    for k, (pins, offset) in enumerate(((4, 0), (4, 4), (2, 8)), start=2):
        far = tags[f"J{k}"] = _plug(d, w1, f"J{k}", pins, f"X{k}")
        for pin in range(1, pins + 1):
            d.wire(j1[str(offset + pin)], far[str(pin)], wire=(WH, 0.5))
    assert _drawn(d, w1, tmp_path / "cover.md") == []
    top, bottom, pins = _order(d, w1, tmp_path / "cover.md", tags)
    assert (top, bottom) == (["J1"], ["J2", "J3", "J4"])
    assert pins["J1"] == [str(n) for n in range(1, 11)]
    assert pins["J4"] == ["1", "2"]


def test_a_plug_fanned_out_to_three_headers_alternating_draws(tmp_path: Path) -> None:
    """(b) A 14-pin plug to three 2-pin headers' own pins, alternating: no ERROR."""
    d = _design(tmp_path)
    d.location("C1", "Cabinet")
    w1 = d.harness("W1", place="C1")
    j1 = _plug(d, w1, "J1", 14, "X1")
    tags = {"J1": j1}
    for k, (a, b) in enumerate((("3", "10"), ("4", "11"), ("5", "12")), start=2):
        far = tags[f"X{k}"] = d.device(f"X{k}", "T-HDR-2")
        d.wire(j1[a], far["1"], wire=(WH, 0.25))
        d.wire(j1[b], far["2"], wire=(WH, 0.25))
    assert _drawn(d, w1, tmp_path / "cover.md") == []
    _, _, pins = _order(d, w1, tmp_path / "cover.md", tags)
    assert pins["J1"][:6] == ["3", "4", "5", "10", "11", "12"]
    assert pins["J1"][6:] == [str(n) for n in (1, 2, 6, 7, 8, 9, 13, 14)]


class _Board(NamedTuple):
    X1: Any
    X2: Any


@fr.unit("t-board", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _board(u: Any) -> _Board:
    """A nested board unit whose 14-pin and 6-pin headers are its interface."""
    x1 = u.device("X1", "T-HDR-14", interface=True)
    x2 = u.device("X2", "T-HDR-6", interface=True)
    return _Board(x1, x2)


def test_two_groups_of_plain_wires_draw_in_core_order(tmp_path: Path) -> None:
    """(c) 18 wires: a 14-pin plug fans to three plugs on one device, apart from a pair.

    The 14-pin and 6-pin plugs sit on a nested board unit's headers; the other four plugs sit on
    the four connector functions of one device. Pins 1 to 13 read in order, the ends J3, J4, J5.
    """
    d = _design(tmp_path)
    d.location("C1", "Cabinet")
    board = d.add(_board, "U1", place="C1")
    quad = d.device("A1", "T-QUAD")
    w1 = d.harness("W1", place="C1")
    contacts: dict[str, Any] = {"contacts": "DEMO-CRIMP-F"}
    j1 = d.device("J1", "T-PLG-14", parent=w1, **contacts)
    j2 = d.device("J2", "T-PLG-6", parent=w1, **contacts)
    d.mate(j1, board.X1)
    d.mate(j2, board.X2)
    tags = {"J1": j1, "J2": j2}
    for tag, pins, fn in (("J3", 16, "x1"), ("J4", 4, "x2"), ("J5", 10, "x3"), ("J6", 6, "x4")):
        tags[tag] = d.device(tag, f"T-PLG-{pins}", parent=w1, **contacts)
        d.mate(tags[tag], getattr(quad, fn))
    runs = (
        ("J1", range(1, 7), "J3", (1, 2, 3, 9, 10, 11)),
        ("J1", range(7, 10), "J4", (1, 3, 4)),
        ("J1", range(10, 14), "J5", (1, 2, 6, 7)),
        ("J2", range(1, 6), "J6", (1, 3, 4, 5, 6)),
    )
    for near, near_pins, far, far_pins in runs:
        for a, b in zip(near_pins, far_pins, strict=True):
            d.wire(tags[near][str(a)], tags[far][str(b)], wire=(WH, 0.5))
    cover = tmp_path / "cover.md"
    assert _drawn(d, w1, cover) == []
    top, bottom, pins = _order(d, w1, cover, tags)
    assert pins["J1"] == [str(n) for n in range(1, 15)]
    assert [t for t in bottom if t in ("J3", "J4", "J5")] == ["J3", "J4", "J5"]
    assert {"J2", "J6"} <= {*top, *bottom}
