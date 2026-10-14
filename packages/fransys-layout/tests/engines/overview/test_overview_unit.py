"""The overview engine on the small hand models: empty and lineless, exactly-one subject, keys.

Each test names what breaks it.
"""

from functools import cache

import fransys_author
import fransys_parts
import pytest
from diagram_models import chain, fanout, one_box, station

from fransys_layout.engines.overview import lay_out_overview
from fransys_model.derive.passes.numbering import number as number_pass
from fransys_model.kernel import freeze, merge
from fransys_model.layout import OverviewBox, OverviewLine, OverviewView, layout_of


@cache
def _empty():
    """The demo parts and a design with a project and a revision, and nothing else."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(title="Empty", number="P-0", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-07", text="First issue", created="XX")
    return number_pass(freeze(merge(parts, d.draft())))[0]


def _written(model):
    return [len(layout_of(model, kind)) for kind in (OverviewView, OverviewBox, OverviewLine)]


def test_an_empty_model_writes_no_records_and_no_finding():
    """Breaks if an empty model raises, writes a view, or reports a finding."""
    out, findings = lay_out_overview(_empty())
    assert findings == ()
    assert _written(out) == [0, 0, 0]


def test_a_single_box_with_no_line_writes_nothing():
    """Breaks if a lineless box is drawn at the system level or raises.

    The system level draws only boxes joined by a cable; the one core of `one_box` joins two
    ports of the same motor, so it draws neither a box nor a line.
    """
    out, findings = lay_out_overview(one_box())
    assert findings == ()
    assert _written(out) == [0, 0, 0]


@pytest.mark.parametrize(
    "build", [station, lambda: chain(4), fanout], ids=["station", "chain4", "fanout"]
)
def test_every_stub_box_hangs_on_a_box_of_its_view(build):
    """Breaks if a stub box names no inside box, or one that is not in its view.

    The station has stubs. A level box has no `stub_of`; a stub box's `stub_of` is a level box.
    """
    out, _ = lay_out_overview(build())
    boxes = layout_of(out, OverviewBox)
    assert boxes
    stubs = [b for b in boxes.values() if b.stub_of is not None]
    for box in stubs:
        assert box.stub_of is not None
        inside = boxes[box.stub_of]
        assert inside.view == box.view
        assert inside.stub_of is None
    if build is station:
        assert stubs


@pytest.mark.parametrize(
    "build", [station, lambda: chain(4), fanout], ids=["station", "chain4", "fanout"]
)
def test_two_runs_key_the_same_records(build):
    """Breaks if a record's `key` or id changes between two runs of the same model.

    Each kind is compared as a map from `key` to record, and every key must be unique.
    """
    model = build()
    first, _ = lay_out_overview(model)
    second, _ = lay_out_overview(model)
    for kind in (OverviewView, OverviewBox, OverviewLine):
        a = {r.key: r for r in layout_of(first, kind).values()}
        b = {r.key: r for r in layout_of(second, kind).values()}
        assert len(a) == len(layout_of(first, kind))
        assert a == b
