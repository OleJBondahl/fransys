"""Field case: a contact written in another block's series draws in that block.

The engineering shape: a relay K1 is made in block A (its coil on the 24 V rail); block B wires
a series from the rail through a fuse, K1's contact and a lamp. A second shape wires the contacts
of two relays, K4 (block A) and K5 (block C), in one series of block B. A third wires one
contact in the series of two blocks. A fourth wires a one-function device (a fuse) made in A.

The bug (reported against v0.19.1): the contact drew in its device's block A, so block B's path
crossed blocks. When A and B landed on different pages the wire between the fuse and the contact
was cut into a marker pair and `CHAIN_BROKEN` warned.

The rule (decision author-0050): a function wired by a `d.series` written inside block B draws in
block B, as `d.layout.draw_in` would say; the device, the designation (=A-K1) and the coil's
contact table stay, the table pointing to the contact's page in B. Only a function of a device
with two or more functions follows a series: a one-function device stays with its block. Series
in two blocks wiring one function leave it in its device's block, with no finding. An explicit
`d.layout.draw_in` wins.
"""

from typing import TYPE_CHECKING, Any, NamedTuple
lazy from pathlib import Path

import fransys as fr
from _drawn_pages import drawn_pages
from _tables_on import TABLES_ON

from fransys_model.layout import GroupHint, layout_of
from fransys_model.vocab.tables import aspect_nodes, functions

if TYPE_CHECKING:
    from fransys_layout.drawing import Drawing, DrawnSymbol

_UNIT: dict[str, Any] = {
    "revision": 1,
    "interface_version": 1,
    "date": "2026-01-01",
    "text": "first",
    "by": "AB",
}
_FILL = {
    "one": 3,
    "two": 3,
    "both": 3,
    "single": 3,
}  # coils in block A that push B's path to the next page
_RELAY = "DEMO-RLY-2CO-24"
_NOT_TAGGED = ("junction-dot", "contact-head", "power-supply", "ground", "protective-earth")


class _Io(NamedTuple):
    g1: Any


def _unit(shape: str, fill: int, *, explicit: bool = False) -> Any:
    @fr.unit("demo-pb", **_UNIT)
    def _pb(d: Any) -> _Io:
        g1 = d.device("G1", "DEMO-PSU-24")
        dc = d.dc_supply("24VDC", g1)
        with d.function("A", "Relays") as block_a:
            k4 = d.device("K4", _RELAY)
            d.series(dc.plus, k4.coil, dc.minus, wire=0.75)
            f2 = d.device("F2", "DEMO-FUSE-DC-160") if shape == "single" else None
            for i in range(fill):
                d.series(dc.plus, d.device(f"KX{i}", _RELAY).coil, dc.minus, wire=0.75)
        with d.function("C", "More relays"):
            k5 = d.device("K5", _RELAY)
            d.series(dc.plus, k5.coil, dc.minus, wire=0.75)
        with d.function("B", "Load"):
            f1 = d.device("F1", "DEMO-FUSE-DC-160")
            h1 = d.device("H1", "DEMO-LAMP-24")
            contacts = (k4.co_1.no, k5.co_1.no) if shape == "two" else (k4.co_1.no,)
            extra = (f2.element,) if f2 is not None else ()
            d.series(dc.plus, f1.element, *extra, *contacts, h1, dc.minus, wire=0.75)
            if explicit:
                d.layout.draw_in(k4.co_1, block_a)
        if shape == "both":
            with d.function("D", "Second load"):
                h2 = d.device("H2", "DEMO-LAMP-24")
                d.series(dc.plus, k4.co_1.nc, h2, dc.minus, wire=0.75)
        return _Io(g1)

    return _pb


def _build(shape: str, tmp_path: Path, *, explicit: bool = False) -> fr.BuildResult:
    (tmp_path / "c.md").write_text("# c\n", encoding="utf-8")
    d = fr.design("demo_parts")
    d.add(_unit(shape, _FILL[shape], explicit=explicit), "U1")
    cover = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-pb", cover=tmp_path / "c.md")
    return fr.build(d, cover, settings=TABLES_ON)


def _fn(result: fr.BuildResult, device: str, name: str) -> Any:
    (one,) = (
        f.id
        for f in functions(result.model).values()
        if "/".join(f.key).endswith(f"/{device}/fn/{name}")
    )
    return one


def _tagged(result: fr.BuildResult, device: str) -> list[tuple[Any, Drawing, DrawnSymbol]]:
    """Each page, Drawing and symbol whose tag text names `device`: the symbol nearest its tag."""
    found = []
    for pid, d in drawn_pages(result.model).items():
        for text in d.texts:
            if text.kind == "TAG" and text.text.endswith(f"-{device}"):
                near = min(
                    (s for s in d.symbols if s.key not in _NOT_TAGGED),
                    key=lambda s: abs(s.x - text.box.x) + abs(s.y - text.box.y),
                )
                found.append((pid, d, near))
    return found


def _page(result: fr.BuildResult, device: str, name: str) -> Any:
    """The page of the drawn `name` of `device`; a coil is its operating device."""
    key = "operating-device" if name == "coil" else None
    pages = {
        pid
        for pid, _, s in _tagged(result, device)
        if (s.key == key if key else s.key != "operating-device")
    }
    (one,) = pages
    return one


def _codes(result: fr.BuildResult) -> set[str]:
    return {f.code for f in result.findings}


def _table_pages(result: fr.BuildResult, device: str) -> set[Any]:
    """The pages that hold a drawn row of the contact table under the coil of `device`."""
    pages = set()
    for pid, d, coil in _tagged(result, device):
        if coil.key != "operating-device":
            continue
        for head in (s for s in d.symbols if s.key == "contact-head" and abs(s.x - coil.x) <= 8):
            if any(v[:1].isdigit() and "N/A" not in v for _, v in head.slots):
                pages.add(pid)
    return pages


def test_a_contact_in_blocks_series_stands_with_the_path_and_the_table_names_its_page(
    tmp_path: Path,
) -> None:
    result = _build("one", tmp_path)
    assert "CHAIN_BROKEN" not in _codes(result)
    assert _page(result, "K4", "co_1") == _page(result, "F1", "element")
    assert _table_pages(result, "K4") == {_page(result, "F1", "element")}


def test_contacts_of_relays_from_two_blocks_stand_in_the_third_blocks_series(
    tmp_path: Path,
) -> None:
    result = _build("two", tmp_path)
    assert "CHAIN_BROKEN" not in _codes(result)
    page = _page(result, "F1", "element")
    assert _page(result, "K4", "co_1") == page
    assert _page(result, "K5", "co_1") == page
    assert _table_pages(result, "K5") == {page}


def test_a_contact_in_two_blocks_series_stays_in_its_device_block(
    tmp_path: Path,
) -> None:
    result = _build("both", tmp_path)
    contact = _fn(result, "K4", "co_1")
    assert contact not in {h.function for h in layout_of(result.model, GroupHint).values()}


def test_a_one_function_device_wired_in_another_blocks_series_stays_in_its_block(
    tmp_path: Path,
) -> None:
    result = _build("single", tmp_path)
    fuse = _fn(result, "F2", "element")
    assert fuse not in {h.function for h in layout_of(result.model, GroupHint).values()}


def test_an_explicit_draw_in_wins_over_the_series(tmp_path: Path) -> None:
    result = _build("one", tmp_path, explicit=True)
    contact = _fn(result, "K4", "co_1")
    (hint,) = (h for h in layout_of(result.model, GroupHint).values() if h.function == contact)
    assert aspect_nodes(result.model)[hint.group].label == "A"


def test_the_contact_keeps_its_device_and_designation(tmp_path: Path) -> None:
    """Drawing in B changes no designation: the contact is still the device K4 of block A."""
    result = _build("one", tmp_path)
    tags = {f.id: "/".join(f.key) for f in functions(result.model).values()}
    assert tags[_fn(result, "K4", "co_1")].endswith("U1/A/K4/fn/co_1")
    assert tags[_fn(result, "K4", "coil")].endswith("U1/A/K4/fn/coil")
