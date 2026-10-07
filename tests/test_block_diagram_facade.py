"""The block diagram through the facade (BD-3 F1, decision 0119).

The diagram lays out only for a kept BLOCK_DIAGRAM page; the SYSTEM preset keeps it; a kept page
over a diagram that cannot be drawn is `DOCUMENT_NO_DRAWINGS`, a reading with no line is silent.
"""

import functools
import sys
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    # `--import-mode=importlib` (root pyproject.toml) never puts this folder on `sys.path`.
    sys.path.insert(0, str(_TESTS_DIR))

import fransys as fr  # noqa: E402 -- after the sys.path insert
import fransys_author  # noqa: E402 -- ditto
import fransys_parts  # noqa: E402 -- ditto
from _model_build_cover import _COVER  # noqa: E402 -- ditto
from test_units_worked_example import _PROJECT, pump_cabinet  # noqa: E402 -- ditto

from fransys_model.layout import DiagramSheet, layout_of  # noqa: E402 -- ditto
from fransys_model.vocab import DocumentPreset, PageKind  # noqa: E402 -- ditto


def _design(leaves: int):
    """A cabinet-less system: motor `M0` joined by one cable to each of `leaves` motors."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-10-07", text="First issue", created="XX")
    loc, grp = d.location("C1", "Cabinet"), d.group("EXT", "Field")
    hub = d.item("DEMO-MOTOR-4KW", tag="M0", group=grp)
    for n in range(1, leaves + 1):
        leaf = d.item("DEMO-MOTOR-4KW", tag=f"M{n}", group=grp)
        d.cable("DEMO-CBL-4G1.5", tag=f"W{n}").core(1, hub["U"], leaf["U"])
    return parts, d.draft(), loc


def _built(leaves: int, document):
    parts, draft, loc = _design(leaves)
    return fr.build(parts, draft, document(loc))


def _system(**kwargs):
    return lambda _loc: fr.document(DocumentPreset.SYSTEM, None, cover=_COVER, **kwargs)


@functools.cache
def _system_build():
    return _built(3, _system())


def _codes(result) -> set[str]:
    return {f.code for f in fr.check(result)}


def test_a_system_document_lays_out_and_writes_its_diagram(tmp_path):
    result = _system_build()
    assert layout_of(result.model, DiagramSheet)
    assert "DOCUMENT_NO_DRAWINGS" not in _codes(result)
    inter = tmp_path / "inter"
    fr.write(result, tmp_path / "out", intermediates=inter)
    (source,) = [p.read_text(encoding="utf-8") for p in sorted(inter.glob("*.typ"))]
    assert "#page(width: 594mm, height: 420mm" in source


def test_a_build_without_a_kept_diagram_page_holds_no_diagram_record():
    """Probe: `needs_diagram_layout` always true, and this fails."""
    without = _built(3, _system(remove=(PageKind.BLOCK_DIAGRAM,)))
    assert not layout_of(without.model, DiagramSheet)
    other = lambda loc: fr.document(DocumentPreset.CABINET_SCHEMATIC, loc, cover=_COVER)  # noqa: E731 -- one-use
    assert not layout_of(_built(3, other).model, DiagramSheet)


def test_add_puts_the_page_on_a_document_that_does_not_carry_it():
    added = _built(
        3,
        lambda loc: fr.document(
            DocumentPreset.CABINET_SCHEMATIC, loc, cover=_COVER, add=(PageKind.BLOCK_DIAGRAM,)
        ),
    )
    assert layout_of(added.model, DiagramSheet)


def test_a_kept_diagram_page_over_an_undrawable_diagram_is_document_no_drawings():
    """25 leaves make a column taller than a sheet: no record, so the kept page is an ERROR."""
    result = _built(25, _system())
    assert not layout_of(result.model, DiagramSheet)
    assert "DOCUMENT_NO_DRAWINGS" in _codes(result)


def test_a_reading_with_no_line_gives_no_page_and_no_finding():
    result = _built(0, _system())
    assert not layout_of(result.model, DiagramSheet)
    assert "DOCUMENT_NO_DRAWINGS" not in _codes(result)


def test_the_cabinets_own_document_writes_no_diagram_record_and_no_page(tmp_path):
    """Acceptance 4: a unit document keeps no BLOCK_DIAGRAM page by default: nothing is laid out."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    pump_cabinet(d.scope("p"), name="C1")
    document = fr.document(DocumentPreset.CABINET_SCHEMATIC, "demo-pump-cabinet", cover=_COVER)
    result = fr.build(parts, d.draft(), document)
    assert not layout_of(result.model, DiagramSheet)
    inter = tmp_path / "inter"
    fr.write(result, tmp_path / "out", intermediates=inter)
    assert all("height: 420mm" not in p.read_text(encoding="utf-8") for p in inter.glob("*.typ"))
