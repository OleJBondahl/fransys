"""The page Drawings built straight from the CoreLayout (FLIP-NOW F7, el-0039). (known: DRAWING_SHORTS_NETS KI-417)

Checked on the demo skid, the corpus DI panel (10 channels), remote IO (several sets, each with a
page 1) and an eight-starter motor feeder (cross-page markers and links): the pages come in print
"""

import dataclasses
import importlib
import importlib.util
from pathlib import Path

import fransys as fr
import pytest
from _direct_case import built_with_unlaid, laid_again
from _motor_feeder_case import motor_feeder_case_drafts
from _page_drawings import page_drawings

from fransys_model.derive import ordered_pages

ROOT = Path(__file__).resolve().parent.parent
SKID = ROOT / "examples" / "demo-skid" / "skid.py"


def _skid() -> object:
    spec = importlib.util.spec_from_file_location("demo_skid_direct", SKID)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return fr.build(*module.design())


def _remote_io() -> object:
    module = importlib.import_module("placement_corpus.standard.remote_io")
    return fr.build(*module.design())


def _panel() -> object:
    """The corpus DI panel at its smallest size (10 channels); two sets, one of them unlaid."""
    module = importlib.import_module("placement_corpus.standard.panel_di16p")
    return fr.build(*module.design(channels=10))


def _both(build_it):
    """(facade drawings, fresh drawings, laid) of one design."""
    result, unlaid = built_with_unlaid(build_it)
    laid, drawn = laid_again(unlaid)
    return page_drawings(result), drawn, laid


def _feeder() -> object:
    # This 8-starter build is MARKER_UNPLACED 2 (KI-466).
    return fr.build(*motor_feeder_case_drafts(8))


BUILDS = {
    "skid": _skid,
    "panel": _panel,
    "remote_io": _remote_io,  # several sets, each with a page 1
    "feeder": _feeder,  # two pages: cross-page markers
}


@pytest.fixture(
    scope="module",
    params=[
        "skid",
        pytest.param("panel", marks=pytest.mark.private_input),  # reads internal/ (R462)
        pytest.param("remote_io", marks=pytest.mark.private_input),
        "feeder",
    ],
)
def pair(request: pytest.FixtureRequest):
    return _both(BUILDS[request.param])


def _same(old, new):
    assert list(old) == list(new)
    for page in old:
        assert new[page] == old[page]


def test_the_facade_drawings_equal_a_fresh_run_page_for_page(pair):
    old, new, _ = pair
    assert old
    _same(old, new)


def test_the_pages_come_in_print_order_and_every_one_has_content(pair):
    _, new, laid = pair
    assert list(new) == [p.id for p in ordered_pages(laid) if p.id in new]
    assert all(drawing.symbols for drawing in new.values())


def test_a_changed_symbol_is_caught(pair):
    old, new, _ = pair
    page = next(iter(new))
    first, *rest = new[page].symbols
    broken = dict(new)
    broken[page] = dataclasses.replace(new[page], symbols=(dataclasses.replace(first, x=first.x + 1), *rest))
    with pytest.raises(AssertionError):
        _same(old, broken)
