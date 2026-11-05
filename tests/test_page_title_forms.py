"""`page_title_forms`: where a drawing page's title comes from and how it shortens (PT1 to PT5).

Built through the public API on invented parts; the model is read with `fransys_model.derive`.
One build per module: three blocks on one page, and a page with no block.
"""

from typing import TYPE_CHECKING

import fransys as fr
import pytest

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
