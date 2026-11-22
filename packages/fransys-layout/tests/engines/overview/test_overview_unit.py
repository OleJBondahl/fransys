"""The overview engine on the small hand models: empty and lineless, and two runs equal.

Each test names what breaks it.
"""

from functools import cache

import fransys_parts
import pytest
from diagram_models import chain, fanout, one_box, station
from fransys_author.design import Design
from library_records import freeze

from electrical_symbols import LIBRARY
from fransys_layout.engines.overview import lay_out_overview
from fransys_model.derive.passes.numbering import number as number_pass
from fransys_model.kernel import merge


@cache
def _empty():
    """The demo parts and a design with a project and a revision, and nothing else."""
    parts = fransys_parts.load("demo_parts")
    d = Design(parts)
    d.project(title="Empty", number="P-0", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-07", text="First issue", created="XX")
    return number_pass(freeze(merge(parts, d.draft())))[0]


@pytest.mark.parametrize("model", [_empty, one_box], ids=["empty-model", "single-box-with-no-line"])
def test_a_model_with_no_line_places_no_view_and_no_finding(model):
    """Breaks if an empty model, or a lineless box, raises, places a view or reports a finding.

    The system level draws only boxes joined by a cable; the one core of `one_box` joins two
    ports of the same motor, so it draws neither a box nor a line.
    """
    out, findings = lay_out_overview(model(), LIBRARY)
    assert findings == ()
    assert out.views == ()


@pytest.mark.parametrize("build", [station, lambda: chain(4), fanout], ids=["station", "chain4", "fanout"])
def test_two_runs_place_the_same_views(build):
    """Breaks if a placed view differs between two runs of the same model, or none is placed."""
    model = build()
    first, _ = lay_out_overview(model, LIBRARY)
    second, _ = lay_out_overview(model, LIBRARY)
    assert first.views
    assert first == second
