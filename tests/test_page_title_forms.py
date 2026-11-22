"""`page_title_forms`: where a drawing page's title comes from and how it shortens (PT1 to PT5).

Built through the public API on invented parts; the model is read with `fransys_model.derive`.
One build per module: three blocks on one page, and a page with no block.
"""

# INK_WITHOUT_CONDUCTOR: an old finding of this file's builds, on KI-1377 (R3538).
from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
import pytest
from fransys.colours import BU

from fransys_model.derive import page_title, page_title_forms
from fransys_model.layout import Page, layout_of

if TYPE_CHECKING:
    from pathlib import Path

    from fransys_model.kernel import Model


def _build(root: Path) -> Model:
    d = fr.design("demo_parts", place="C1")
    cabinet = d.location("C1", "Cabinet")
    relays = []
    for i in range(1, 4):
        with d.function(f"F{i}", f"Relay circuit {i}"):
            relays.append(d.device(f"K{i}", "DEMO-RLY-2CO-24"))
    k1, k2, k3 = relays
    for pin in ("A1", "A2"):  # the coils in parallel: no coil half-wired
        d.series(k1.coil[pin], k2.coil[pin], wire=("WH", 0.75))
        d.series(k2.coil[pin], k3.coil[pin], wire=("WH", 0.75))
    cover = root / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=cover)).model


def _forms(model: Model) -> tuple[str, ...]:
    (page,) = layout_of(model, Page).values()
    return page_title_forms(model, page)


@pytest.fixture(scope="module")
def plain(tmp_path_factory: pytest.TempPathFactory) -> Model:
    return _build(tmp_path_factory.mktemp("plain"))


@pytest.mark.rule("PAGE-TITLE")
def test_blocks_texts_join_longest_first_then_first_to_last(plain: Model) -> None:
    assert _forms(plain) == (
        "Relay circuit 1, Relay circuit 2, Relay circuit 3",
        "Relay circuit 1 to 3",
    )


def test_page_title_is_the_first_form(plain: Model) -> None:
    (page,) = layout_of(plain, Page).values()
    assert page_title(plain, page) == _forms(plain)[0]


def test_a_page_with_no_block_reads_its_designations_once_each_in_drawn_order(
    tmp_path: Path,
) -> None:
    d = fr.design("demo_parts", place="C1")
    cabinet = d.location("C1", "Cabinet")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
    h1 = d.device("H1", "DEMO-LAMP-24")
    sig = x1.run("SIG", 2)
    d.series(sig[1].inner, h1.lamp["1"], wire=("WH", 0.75))
    d.series(sig[2].inner, h1.lamp["2"], wire=("WH", 0.75))
    cover = tmp_path / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    built = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=cover))
    assert _forms(built.model) == ("-X1, -H1",)


def _strip_model(tmp_path: Path, *, strips: int) -> Model:
    d = fr.design("demo_parts", place="C1")
    cabinet = d.location("C1", "Cabinet")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
    h1 = d.device("H1", "DEMO-LAMP-24")
    sig = x1.run("SIG", 2)
    d.series(sig[1].inner, h1.lamp["1"], wire=("WH", 0.75))
    if strips == 1:
        d.series(sig[2].inner, h1.lamp["2"], wire=("WH", 0.75))
    else:
        x2 = d.terminal_strip("X2", "DEMO-TB-2.5", 4)
        d.series(sig[2].inner, x2.run("SIG", 1)[1].inner, wire=("WH", 0.75))
        d.series(h1.lamp["2"], x1.run("RET", 1)[1].inner, wire=("WH", 0.75))  # lamp pin 2 returns to X1, not X2: no pin left open
    cover = tmp_path / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=cover)).model


def test_a_terminal_stands_as_its_strip_once(tmp_path: Path) -> None:
    assert _forms(_strip_model(tmp_path, strips=1))[0] == "-X1, -H1"


def test_two_strips_and_a_device_read_each_strip_once(tmp_path: Path) -> None:
    assert _forms(_strip_model(tmp_path, strips=2))[0] == "-X1, -X2, -H1"


class _Strips(NamedTuple):
    X1: fr.TerminalStrip
    X2: fr.TerminalStrip


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB", title="Cabinet")
def _cabinet(u: Any) -> _Strips:
    """Alpha and Charlie, each with an interface strip and a lamp; the system holds Alpha, Bravo and Charlie too."""
    strips = []
    for key, text, tag in (("A", "Alpha", "H1"), ("C", "Charlie", "H3")):
        with u.function(key, text):
            strip = u.terminal_strip(f"X{len(strips) + 1}", "DEMO-TB-2.5", 2, interface=(1, 2))
            lamp = u.device(tag, "DEMO-LAMP-24")
            u.series(strip[1].inner, lamp.lamp["1"], wire=(BU, 0.5))
            u.series(strip[2].inner, lamp.lamp["2"], wire=(BU, 0.5))
        strips.append(strip)
    return _Strips(*strips)


def test_one_label_under_two_unit_prefixes_stands_in_one_place_on_every_sheet(tmp_path: Path) -> None:
    """PAGE-TITLE-ORDER: the system sheet holds U1's Alpha and Charlie before its own Alpha, Bravo and Charlie; the title reads A, B, C."""
    d = fr.design("demo_parts", place="EXT")
    d.location("EXT", "External")
    d.project(title="Plant", number="P-1", customer="Demo Co", revision=1, author="d")
    d.revision(1, date="2026-01-01", text="first", created="AB")
    cab = d.add(_cabinet, "U1", place=None)
    lamps = []
    for key, text in (("A", "Alpha"), ("B", "Bravo"), ("C", "Charlie")):
        with d.function(key, text):
            lamps.append(d.device(f"H{len(lamps) + 1}", "DEMO-LAMP-24"))
    h1, h2, h3 = lamps
    d.series(cab.X1[1].outer, h1.lamp["1"], wire=(BU, 0.5))
    d.series(h1.lamp["2"], h2.lamp["1"], wire=(BU, 0.5))
    d.series(h2.lamp["2"], h3.lamp["1"], wire=(BU, 0.5))
    d.series(h3.lamp["2"], cab.X1[2].outer, wire=(BU, 0.5))
    d.series(cab.X2[1].outer, h2.lamp["1"], wire=(BU, 0.5))
    d.series(cab.X2[2].outer, h3.lamp["1"], wire=(BU, 0.5))
    cover = tmp_path / "cover.md"
    cover.write_text("# Plant\n", encoding="utf-8")
    model = fr.build(d, fr.document(fr.DocumentPreset.SYSTEM, None, cover=cover)).model
    titles = [page_title(model, page) for page in layout_of(model, Page).values()]
    assert "Alpha, Bravo, Charlie" in titles, titles
