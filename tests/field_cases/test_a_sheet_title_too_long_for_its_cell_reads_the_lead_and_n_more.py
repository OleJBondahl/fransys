"""Field case: a sheet title whose joined block texts do not fit the title cell reads the lead and "n more".
The bug: the frame cut the joined title with an ellipsis and raised TITLE_BLOCK_TEXT_OVERFLOW, as neither form fitted the cell.
Fixed by layout-0268 (PAGE-TITLE-FIT T1), the title is the joined texts while they fit, else the lead's text and "and n more"."""

from itertools import pairwise

import fransys as fr
import pytest
from _model_build_cover import unit_document

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
    relays, supplies = [], []
    for i, text in enumerate(_TEXTS, 1):
        with d.function(f"F{i}", text):
            relays.append(d.device(f"K{i}", "DEMO-RLY-2CO-24"))
            if i == 1:
                supplies.append(d.device("T1", "DEMO-PSU-24"))
    (psu,) = supplies
    for a, b in pairwise(relays):
        d.series(a.coil["A2"], b.coil["A1"], wire=("WH", 0.75))
    d.series(psu.output["+"], relays[0].coil["A1"], wire=("WH", 0.75))
    d.series(relays[-1].coil["A2"], psu.output["-"], wire=("WH", 0.75))
    return fr.build(d, unit_document(cabinet))


def test_the_title_ends_in_the_lead_and_n_more(built: fr.BuildResult) -> None:
    (page,) = layout_of(built.model, Page).values()
    assert page_title_forms(built.model, page)[-1] == f"{_TEXTS[0]} and 4 more"


def test_no_title_block_overflow_is_raised(built: fr.BuildResult) -> None:
    assert not [f for f in fr.check(built) if f.code == "TITLE_BLOCK_TEXT_OVERFLOW"]
