"""S17, S20: a C21 run's box stands as its marker box, and the slot labels clear it.

The fixture is the field case `field_cases/test_changeover_throws_to_two_strips.py` with no
`Unit` around it: poles 3 and 4 of a changeover, each throw wired to its own terminal of a field
strip at another location. Its one page draws K1's four throw stubs as one C21 run (S14) and
each strip terminal's stub back to K1. A run's box stands as its marker box (S17, S20): it is
a marker of the page (`Layout.markers`, `shared_box`), so the first slot call (tags and
markings) and the second (S18) hold it in their `occupied`.

The rule: no K1 marking and no terminal tag stands over a marker's box, run box or stub box,
and each is placed (no `LABEL_UNPLACED`). Markers standing over each other are not this
rule's, so no test here reads one marker over another.
"""

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest import mock

import pytest

from fransys_layout.engines.schematic import engine
from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.stages.types import LabelKind
from fransys_model.vocab.tables import functions, ports

if TYPE_CHECKING:
    from fransys_layout.geometry import Box

# `--import-mode=importlib` (root pyproject.toml) never puts a test directory on `sys.path`, and
# ty cannot resolve a `sys.path` insert; the field case's own build is loaded from its file.
_FIELD_CASE = (
    Path(__file__).resolve().parent / "field_cases" / "test_changeover_throws_to_two_strips.py"
)
_spec = importlib.util.spec_from_file_location("_changeover_field_case_band", _FIELD_CASE)
assert _spec is not None
assert _spec.loader is not None
_field_case = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_field_case)


@pytest.fixture(scope="module")
def page(tmp_path_factory) -> tuple[Any, Any, tuple[Any, ...]]:
    """The no-unit field case built: the model, the engine's layout and its findings."""
    captured: list[tuple[Any, tuple[Any, ...]]] = []

    def recording_results(model: Any, inputs: Any) -> Any:
        results, findings = stage_results(model, inputs)
        captured.append((results.layout, tuple(findings)))
        return results, findings

    with mock.patch.object(engine, "stage_results", recording_results):
        model = _field_case._build(tmp_path_factory.mktemp("changeover"), in_unit=False).model
    ((layout, findings),) = captured
    return model, layout, findings


def _meet(a: Box, b: Box) -> bool:
    """The interiors of `a` and `b` meet."""
    return (
        a.x < b.x + b.width
        and b.x < a.x + a.width
        and a.y < b.y + b.height
        and b.y < a.y + a.height
    )


def _on_marker(one: Any, boxes: list[tuple[int, int, Box]]) -> bool:
    """`one` meets a marker box of its own sheet; sheets share a frame, not a page."""
    sheet = (one.drawing_set, one.page)
    return any(
        _meet(one.box, box) for drawing_set, page, box in boxes if (drawing_set, page) == sheet
    )


def _parts(page: tuple[Any, Any, tuple[Any, ...]]) -> tuple[list, list, list, list, list]:
    """The marker boxes with their (drawing set, page), K1's four throw markings, the four
    terminal tags, the four contacts' cross-references by contact name (`co_3` and `co_4`, the
    drawn contacts), and the findings."""
    model, layout, findings = page
    boxes = [(marker.drawing_set, marker.page, marker.box) for marker in layout.markers]
    keys = {fid: fn.key for fid, fn in functions(model).items()}
    names = {pid: port.name for pid, port in ports(model).items()}
    markings = [
        one
        for one in layout.labels
        if one.kind is LabelKind.MARKING and names[one.subject] in {"32", "34", "42", "44"}
    ]
    tags = [
        one
        for one in layout.labels
        if one.kind is LabelKind.TAG and one.subject in keys and keys[one.subject][1] == "terminal"
    ]
    references = [
        (keys[one.subject][2], one)
        for one in layout.labels
        if one.kind is LabelKind.CROSS_REFERENCE
        and one.subject in keys
        and keys[one.subject][2] in {"co_3", "co_4"}
    ]
    return boxes, markings, tags, references, list(findings)


def test_k1_markings_and_terminal_tags_stand_clear_of_every_marker_box(
    page: tuple[Any, Any, tuple[Any, ...]],
) -> None:
    """K1's throw markings, the strips' four terminal tags and the cross-references of K1's
    contacts 3 and 4 (the drawn ones; contacts 1 and 2 have no wire, layout-0112) stand clear of
    every marker's box on their own sheet (drawing set and page), and both are placed. A box of
    another sheet shares the frame, not the page, so it is not compared.

    On this page only the second slot call reads the markers: without them in its `occupied`,
    contact 4's reference stands at (203, 116), on a marker box of K1's sheet.
    """
    # UNDO: stages/pagerun.py `finish_page`: drop `*marker_shapes(markers)` from the second slot
    #     call's `occupied`: contact 4's cross-reference stands on the K1 run's box
    boxes, markings, tags, references, findings = _parts(page)
    assert boxes
    assert len(markings) == 4
    assert len(tags) == 4
    assert sorted(name for name, _ in references) == ["co_3", "co_4"]
    for one in (*markings, *tags, *(one for _, one in references)):
        assert not one.unplaced
        assert not _on_marker(one, boxes)
    assert not any(one.unplaced for _, one in references)
    assert not [f for f in findings if f.code == "LABEL_UNPLACED"]
