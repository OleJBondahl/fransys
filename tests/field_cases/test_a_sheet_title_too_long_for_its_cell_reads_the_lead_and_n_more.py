"""Field case: a sheet title whose blocks do not fit the title cell reads the lead and "n more".

The engineering shape: one sheet holds five function blocks of a cabinet, each a relay circuit
with a long, distinct text, wired in a chain.

The bug: the sheet's title joined the five texts, then offered "first to last"; neither fitted
the title cell, so the frame cut the text with "…" and raised `TITLE_BLOCK_TEXT_OVERFLOW`.

The rule (decision layout-0268, PAGE-TITLE-FIT T1): the title is the joined texts while they fit
the cell; when they do not, it is the leading block's text and "and n more". The title then fits
and no finding is raised.
"""

import tempfile
from itertools import pairwise
from pathlib import Path

import fransys as fr
import pytest

from fransys_model.derive import page_title_forms
from fransys_model.layout import Page, layout_of

_TEXTS = (
    "Primary boiler feed water pump circuit",
    "Condensate booster pump circuit",
    "Cooling tower fan circuit",
    "Chemical dosing pump circuit",
    "Secondary heat exchanger circulation circuit",
)


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    cabinet = d.location("C1", "Cabinet")
    relays = []
    for i, text in enumerate(_TEXTS, 1):
        with d.function(f"F{i}", text):
            relays.append(d.device(f"K{i}", "DEMO-RLY-2CO-24"))
    for a, b in pairwise(relays):
        d.detail.wire(a.coil["A2"], b.coil["A1"], wire=("WH", 0.75))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=cover))


def test_the_title_ends_in_the_lead_and_n_more(built: fr.BuildResult) -> None:
    (page,) = layout_of(built.model, Page).values()
    assert page_title_forms(built.model, page)[-1] == f"{_TEXTS[0]} and 4 more"


def test_no_title_block_overflow_is_raised(built: fr.BuildResult) -> None:
    assert not [f for f in fr.check(built) if f.code == "TITLE_BLOCK_TEXT_OVERFLOW"]
