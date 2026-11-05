"""Field case: a contact written in another block's series draws in that block.
The bug: the contact drew in its device's block A, so block B's path crossed blocks and `CHAIN_BROKEN` warned on a page split.
Fixed by author-0050: a function in a `d.series` written in block B draws in block B."""

from typing import TYPE_CHECKING, Any, NamedTuple
lazy from pathlib import Path

import fransys as fr
from _drawn_pages import drawn_pages

from fransys_model.layout import GroupHint, layout_of
from fransys_model.vocab.tables import functions

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


def _unit(shape: str, fill: int) -> Any:
    @fr.unit("demo-pb", **_UNIT)
    def _pb(d: Any) -> _Io:
        g1 = d.device("G1", "DEMO-PSU-24")
        dc = d.dc_supply("24VDC", g1)
        with d.function("A", "Relays"):
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
        if shape == "both":
            with d.function("D", "Second load"):
                h2 = d.device("H2", "DEMO-LAMP-24")
                d.series(dc.plus, k4.co_1.nc, h2, dc.minus, wire=0.75)
        return _Io(g1)

    return _pb


def _build(shape: str, tmp_path: Path) -> fr.BuildResult:
    (tmp_path / "c.md").write_text("# c\n", encoding="utf-8")
    d = fr.design("demo_parts")
    d.add(_unit(shape, _FILL[shape]), "U1")
    cover = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-pb", cover=tmp_path / "c.md")
    return fr.build(d, cover)


def _fn(result: fr.BuildResult, device: str, name: str) -> Any:
    (one,) = (f.id for f in functions(result.model).values() if "/".join(f.key).endswith(f"/{device}/fn/{name}"))
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
    pages = {pid for pid, _, s in _tagged(result, device) if (s.key == key if key else s.key != "operating-device")}
    (one,) = pages
    return one


def _codes(result: fr.BuildResult) -> set[str]:
    return {f.code for f in result.findings}


def test_a_contact_in_blocks_series_stands_with_the_path(
    tmp_path: Path,
) -> None:
    result = _build("one", tmp_path)
    assert "CHAIN_BROKEN" not in _codes(result)
    assert _page(result, "K4", "co_1") == _page(result, "F1", "element")


def test_contacts_of_relays_from_two_blocks_stand_in_the_third_blocks_series(
    tmp_path: Path,
) -> None:
    result = _build("two", tmp_path)
    assert "CHAIN_BROKEN" not in _codes(result)
    page = _page(result, "F1", "element")
    assert _page(result, "K4", "co_1") == page
    assert _page(result, "K5", "co_1") == page


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


def test_the_contact_keeps_its_device_and_designation(tmp_path: Path) -> None:
    """Drawing in B changes no designation: the contact is still the device K4 of block A."""
    result = _build("one", tmp_path)
    tags = {f.id: "/".join(f.key) for f in functions(result.model).values()}
    assert tags[_fn(result, "K4", "co_1")].endswith("U1/A/K4/fn/co_1")
    assert tags[_fn(result, "K4", "coil")].endswith("U1/A/K4/fn/coil")
