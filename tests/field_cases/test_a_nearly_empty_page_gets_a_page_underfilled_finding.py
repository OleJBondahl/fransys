"""Field case: a cabinet page with one lamp on it, in the corner of an otherwise empty page.

The engineering shape: a lamp wired to a terminal in a cabinet. The layout stacks a page from
its top and draws one tier, so the lamp fills a small corner of the A3 page and the rest of the
printed sheet is blank.

The bug: nothing reported it. The build was green, so the author learned of the wasted page, and
the small print that follows from it, only from the printed drawing.

The rule (decision layout-0179): a schematic page whose drawn content covers under half of the
content box gets one `PAGE_UNDERFILLED` finding of severity INFO. Its message gives the share in
whole percent and the naming pass appends the page (V6b); its subjects are the page's
functions. Nothing is moved or scaled.
"""

import re
from typing import TYPE_CHECKING

import fransys as fr

from fransys_model.kernel import Severity
from fransys_model.vocab.tables import functions

if TYPE_CHECKING:
    from pathlib import Path


def _underfilled(tmp_path: Path) -> tuple[fr.BuildResult, list]:
    d = fr.design("demo_parts", place="C1")
    cabinet = d.location("C1", "Cabinet")
    lamp = d.device("P1", "DEMO-LAMP-24")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5")
    d.wire(x1.run("SIG", 1)[1], lamp.lamp["1"], wire=("WH", 0.75))
    (tmp_path / "c.md").write_text("# Cabinet\n", encoding="utf-8")
    document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=tmp_path / "c.md")
    result = fr.build(d, document)
    return result, [f for f in result.findings if f.code == "PAGE_UNDERFILLED"]


def test_a_nearly_empty_page_gets_one_finding_with_its_share_set_and_page(tmp_path: Path) -> None:
    _, (found,) = _underfilled(tmp_path)
    assert found.severity is Severity.INFO
    assert re.fullmatch(
        r"drawn content covers \d+ % of the content box \(\+C1p1: .+\)", found.message
    )


def test_the_subjects_are_the_functions_of_the_page(tmp_path: Path) -> None:
    result, (found,) = _underfilled(tmp_path)
    assert found.subjects
    assert all(subject in functions(result.model) for subject in found.subjects)
