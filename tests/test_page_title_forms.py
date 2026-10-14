"""`page_title_forms`: where a drawing page's title comes from and how it shortens (PT1 to PT5).

Built through the public API on invented parts; the model is read with `fransys_model.derive`.
One build per module: three blocks on one page, a hinted block, hinted devices, a page of
designations only.
"""

from itertools import pairwise
from typing import TYPE_CHECKING

import fransys as fr
import pytest

from fransys_model.derive import page_title, page_title_forms
from fransys_model.layout import Page, layout_of

if TYPE_CHECKING:
    from pathlib import Path

    from fransys_model.kernel import Model


def _build(root: Path, *, hint: str) -> Model:
    d = fr.design("demo_parts", place="C1")
    cabinet = d.location("C1", "Cabinet")
    devices = []
    for i in range(1, 4):
        with d.function(f"F{i}", f"Relay circuit {i}") as group:
            devices.append((group, d.device(f"K{i}", "DEMO-RLY-2CO-24")))
    for (_, a), (_, b) in pairwise(devices):
        d.wire(a.coil["A2"], b.coil["A1"], wire=("WH", 0.75))
    if hint == "block":
        d.layout.page_title(devices[1][0], "Hinted block")
    if hint == "devices":
        d.layout.page_title(devices[1][1], "Second relay")
        d.layout.page_title(devices[0][1], "First relay")
    cover = root / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=cover)).model


def _forms(model: Model) -> tuple[str, ...]:
    (page,) = layout_of(model, Page).values()
    return page_title_forms(model, page)


@pytest.fixture(scope="module")
def plain(tmp_path_factory: pytest.TempPathFactory) -> Model:
    return _build(tmp_path_factory.mktemp("plain"), hint="")


def test_blocks_texts_join_longest_first_then_first_to_last(plain: Model) -> None:
    assert _forms(plain) == (
        "Relay circuit 1, Relay circuit 2, Relay circuit 3",
        "Relay circuit 1 to 3",
    )


def test_page_title_is_the_first_form(plain: Model) -> None:
    (page,) = layout_of(plain, Page).values()
    assert page_title(plain, page) == _forms(plain)[0]


def test_a_hinted_blocks_text_beats_every_blocks_text(tmp_path: Path) -> None:
    assert _forms(_build(tmp_path, hint="block")) == ("Hinted block",)


def test_device_hints_print_in_drawn_order_not_authored_order(tmp_path: Path) -> None:
    assert _forms(_build(tmp_path, hint="devices"))[0] == "First relay, Second relay"


def test_a_page_with_no_block_reads_its_designations_once_each_in_drawn_order(
    tmp_path: Path,
) -> None:
    d = fr.design("demo_parts", place="C1")
    cabinet = d.location("C1", "Cabinet")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
    h1 = d.device("H1", "DEMO-LAMP-24")
    d.wire(x1.run("SIG", 1)[1], h1.lamp["1"], wire=("WH", 0.75))
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
    d.wire(sig[1], h1.lamp["1"], wire=("WH", 0.75))
    if strips == 1:
        d.wire(sig[2], h1.lamp["2"], wire=("WH", 0.75))
    else:
        x2 = d.terminal_strip("X2", "DEMO-TB-2.5", 4)
        d.wire(sig[2], x2.run("SIG", 1)[1], wire=("WH", 0.75))
    cover = tmp_path / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=cover)).model


def test_a_terminal_stands_as_its_strip_once(tmp_path: Path) -> None:
    assert _forms(_strip_model(tmp_path, strips=1))[0] == "-X1, -H1"


def test_two_strips_and_a_device_read_each_strip_once(tmp_path: Path) -> None:
    assert _forms(_strip_model(tmp_path, strips=2))[0] == "-X1, -X2, -H1"
