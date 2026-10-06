"""F5-C, principle 5 (shuffle) on the example-sized fixture of `dd_stability_fixture`.

`freeze` canonicalises, so authoring in another order (the facade variant below) hands the
engine an equal model and proves almost nothing. The real proofs reorder what the engine
reads: the stage inputs, and the insertion order of a model's own tables.
"""

import dataclasses
import importlib.util
import random
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from fransys_layout.engines import lay_out_schematic
from fransys_layout.engines.schematic import run_stages
from fransys_layout.engines.schematic.read import read_inputs
from fransys_model.layout import SymbolPlacement, layout_of

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_model.kernel import Model

_PATH = Path(__file__).with_name("dd_stability_fixture.py")
# Root tests run under `--import-mode=importlib`: load the sibling helper by path, once.
_FIXTURE = sys.modules.get("dd_stability_fixture")
if _FIXTURE is None:
    _SPEC = importlib.util.spec_from_file_location("dd_stability_fixture", _PATH)
    assert _SPEC is not None
    assert _SPEC.loader is not None
    _FIXTURE = importlib.util.module_from_spec(_SPEC)
    sys.modules["dd_stability_fixture"] = _FIXTURE
    _SPEC.loader.exec_module(_FIXTURE)
build = _FIXTURE.build
pages_of = _FIXTURE.pages_of


def test_the_fixture_is_example_sized_and_has_what_the_properties_need() -> None:
    """F5: >= 5 groups, >= 4 pages, two groups on one page, contact images, no ERROR."""
    model = build()
    layout = run_stages(model, read_inputs(model))[0]
    pages = pages_of(model)
    assert len(pages) >= 4
    assert len({group for page in pages for group in page}) >= 5
    assert any(len(page) >= 2 for page in pages)
    assert len(layout_of(model, SymbolPlacement)) >= 50
    assert sum(1 for label in layout.labels if label.slot == "contacts") >= 4


# -- shuffle: the stage inputs ---------------------------------------------------------------


def _reordered(inputs, order: Callable[[tuple], tuple]):
    """`inputs` with every tuple of records in another order: what another iteration gives."""
    changes = {
        f.name: order(getattr(inputs, f.name))
        for f in dataclasses.fields(inputs)
        if isinstance(getattr(inputs, f.name), tuple)
    }
    return dataclasses.replace(inputs, **changes)


def _differences(one: tuple, other: tuple) -> set[str]:
    """Names of the `Layout` fields (and `drawn`, `findings`) that differ between two runs."""
    found = set()
    for name, a, b in zip(("layout", "drawn", "findings"), one, other, strict=True):
        if not dataclasses.is_dataclass(a):
            found |= {name} if a != b else set()
            continue
        found |= {f.name for f in dataclasses.fields(a) if getattr(a, f.name) != getattr(b, f.name)}
    return found


_ORDERS = [
    pytest.param(lambda records: records[::-1], id="reversed"),
    pytest.param(lambda records: records[1::2] + records[::2], id="interleaved"),
]


@pytest.mark.parametrize("order", _ORDERS)
def test_the_layout_is_independent_of_the_order_of_the_stage_inputs(order) -> None:
    """Principle 5: every stage input tuple reordered, the same Layout, drawn and findings out."""
    # UNDO: in stages/images.py::contact_images, drop the sort key of the item
    # groups and of the contacts inside a group (by function id) and this test fails.
    model = build()
    inputs = read_inputs(model)
    assert (
        _differences(run_stages(model, _reordered(inputs, order)), run_stages(model, inputs))
        == set()
    )


@pytest.mark.parametrize("order", _ORDERS)
def test_the_stage_input_shuffle_changes_only_the_order_of_the_labels(order) -> None:
    """Principle 5, all but the known hole: every other field is equal, labels are the same set.

    Not a proof on its own: the engine re-sorts downstream (chains.py, columns.py, the
    partition column order), so no single sort removal made it fail in four mutation tries.
    The proof is the order test above plus `test_the_shuffle_check_can_fail`.
    """
    # UNDO: none found: the engine re-sorts at several layers (defence in depth).
    model = build()
    inputs = read_inputs(model)
    base, shuffled = run_stages(model, inputs), run_stages(model, _reordered(inputs, order))
    assert _differences(shuffled, base) <= {"labels"}
    assert sorted(map(repr, shuffled[0].labels)) == sorted(map(repr, base[0].labels))
    assert len(base[0].placed) >= 50
    assert len(base[0].routes) >= 20


def test_the_shuffle_check_can_fail() -> None:
    """The comparison flags a reordered label tuple, a dropped placement and a dropped finding."""
    # UNDO: change `_differences` to return set() and this test fails.
    model = build()
    layout, drawn, findings = base = run_stages(model, read_inputs(model))
    assert len(layout.labels) >= 2
    reversed_labels = dataclasses.replace(layout, labels=layout.labels[::-1])
    assert _differences((reversed_labels, drawn, findings), base) == {"labels"}
    fewer = dataclasses.replace(layout, placed=layout.placed[1:])
    assert _differences((fewer, drawn, findings), base) == {"placed"}
    assert _differences((layout, drawn[1:], findings), base) == {"drawn"}


# -- shuffle: the insertion order of a model's tables ---------------------------------------


def _with_tables_shuffled(model: Model, seed: int) -> Model:
    """The same model with every table (and the tables of tables) in another insertion order."""
    rng = random.Random(seed)  # noqa: S311 -- a reproducible shuffle, not cryptography

    def shuffled(mapping):
        pairs = list(mapping.items())
        rng.shuffle(pairs)
        return type(mapping)(pairs)

    tables = type(model.tables)(
        (kind, shuffled(table)) for kind, table in shuffled(model.tables).items()
    )
    return dataclasses.replace(model, tables=tables, hashes=shuffled(model.hashes))


@pytest.mark.parametrize("seed", [1, 2])
def test_a_model_whose_tables_are_in_another_order_gives_one_layout(seed: int) -> None:
    """Principle 5 past the freeze: a Model with shuffled tables lays out to the same digest.

    The shuffle is real (the test asserts the table order differs), but the engine re-sorts
    downstream (read/, chains.py, columns.py, the partition column order), so no single sort
    removal made this fail in four mutation tries.
    """
    # UNDO: none found: every downstream stage re-sorts (defence in depth).
    model = build()
    shuffled = _with_tables_shuffled(model, seed)
    assert shuffled == model
    assert list(shuffled.tables["function"]) != list(model.tables["function"])
    once, once_findings = lay_out_schematic(model)
    again, again_findings = lay_out_schematic(shuffled)
    assert again.digests["layout"] == once.digests["layout"]
    assert again_findings == once_findings
    assert {k: v for k, v in again.tables.items() if k.startswith("layout.")} == {
        k: v for k, v in once.tables.items() if k.startswith("layout.")
    }
    assert len(layout_of(again, SymbolPlacement)) >= 50


def test_authoring_the_design_in_the_other_order_gives_the_same_layout() -> None:
    """WEAK, not the shuffle proof: `freeze` canonicalises, so the engine sees an equal model.

    Kept as a facade-level regression (groups, items and wires added backwards): same digest and
    every layout record equal. It cannot fail on an engine ordering defect: `freeze` erases the
    order, and the engine re-sorts downstream anyway (no mutation of a sort made it fail).
    """
    # UNDO: none found: freeze canonicalises (only freeze keeping authoring order fails it).
    forward, backward = build(), build(reverse=True)
    assert backward.digests["layout"] == forward.digests["layout"]
    for kind in ("symbol_placement", "route", "label", "link_marker", "page"):
        assert backward.tables[f"layout.{kind}"] == forward.tables[f"layout.{kind}"]
    assert len(forward.tables["layout.page"]) >= 4
