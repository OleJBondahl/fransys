"""The findings layer of the overview page (OVERVIEW O18).

The page's data holds, per view, the worst severity and the count on each box and line a finding
names. A subject not drawn on a view counts on its nearest drawn ancestor box. Each test names what
breaks it.
"""

import json
import re
from typing import Any

import fransys as fr
import fransys_parts
from fransys import pipeline
from fransys_overview import html
from test_overview_page import _data, _laid
from test_units_worked_example import _system_design

from fransys_model.derive import overview_graph
from fransys_model.kernel import Finding, Severity
from fransys_model.vocab import conductors, ports


def _finding(severity: Severity, *subjects: Any) -> Finding:
    return Finding(code="DEMO_FINDING", severity=severity, subjects=subjects, message="demo")


def _page(*findings: Finding) -> dict[str, Any]:
    found = re.search(r'id="overview-data">(.*?)</script>', html(_laid()[0], findings=findings))
    assert found is not None
    return json.loads(found.group(1))


def _item_ix(label: str) -> int:
    return next(i for i, row in enumerate(_data()["items"]) if row["label"] == label)


def _flags(data: dict[str, Any], view: int) -> dict[int, list[Any]]:
    return {at: [sev, n] for at, sev, n, *_ in data["findings"][view][0]}


def _view_with(data: dict[str, Any], kind: str, ix: int, mode: str = "plain") -> tuple[int, int]:
    """The first view of `mode` with a box of reference `[kind, ix]`, and that box."""
    for v, view in enumerate(data["views"]):
        for b, box in enumerate(view["boxes"]):
            if box["ref"] == [kind, ix] and box["at"] is None and view["mode"] == mode:
                return v, b
    raise AssertionError((kind, ix))


def test_a_finding_puts_its_severity_on_the_box_it_names() -> None:
    """Breaks if the severity lands on another box or in another view than the item's own."""
    node = overview_graph(_laid()[0]).nodes[0]
    data = _page(_finding(Severity.WARNING, node.item))
    view, box = _view_with(data, "item", 0)
    assert _flags(data, view) == {box: ["warning", 1]}


def test_the_number_counts_the_worst_severity_and_the_list_holds_all() -> None:
    """Breaks if a milder finding is summed into the number or left out of the list (O18)."""
    item = overview_graph(_laid()[0]).nodes[0].item
    found = (_finding(Severity.ERROR, item), _finding(Severity.ERROR, item))
    data = _page(*found, _finding(Severity.INFO, item))
    view, box = _view_with(data, "item", 0)
    assert _flags(data, view)[box] == ["error", 2]
    listed = next(f for f in data["findings"][view][0] if f[0] == box)[3]
    assert listed == [
        ["error", "DEMO_FINDING", 2, ["demo", "demo"]],
        ["info", "DEMO_FINDING", 1, ["demo"]],
    ]


def test_a_subject_not_drawn_counts_on_its_nearest_drawn_ancestor() -> None:
    """Breaks if a terminal's finding is lost where only its unit is drawn (the system level)."""
    model = _laid()[0]
    terminal = overview_graph(model).nodes[_item_ix("-X2:1")].item
    data = _page(_finding(Severity.ERROR, terminal))
    own_view, own = _view_with(data, "item", _item_ix("-X2:1"))
    assert _flags(data, own_view) == {own: ["error", 1]}
    unit = data["items"][_item_ix("-X2:1")]["unit"]
    system, box = _view_with(data, "unit", unit)
    assert _flags(data, system) == {box: ["error", 1]}
    assert data["views"][system]["unit"] is None


def test_a_port_finding_stands_on_the_box_of_its_item() -> None:
    """Breaks if a port subject is not resolved to the item that owns it."""
    model = _laid()[0]
    port = next(iter(ports(model)))
    data = _page(_finding(Severity.WARNING, port))
    assert any(flags for flags in (_flags(data, v) for v in range(len(data["views"]))))


def test_a_conductor_finding_stands_on_the_line_that_joins_its_ends() -> None:
    """Breaks if a conductor's badge goes to a box, or to a line that does not join its ends."""
    model = _laid()[0]
    data = _page(*(_finding(Severity.ERROR, c) for c in conductors(model)))
    lines = [(v, at) for v, rows in enumerate(data["findings"]) for at, *_ in rows[1]]
    assert lines
    for v, at in lines:
        line = data["views"][v]["lines"][at]
        assert line["a"] != line["b"]


def test_no_finding_drawn_means_no_findings_data() -> None:
    """Breaks if the switch would show for a page with nothing to badge."""
    assert _page()["findings"] is None
    assert _page(_finding(Severity.ERROR))["findings"] is None


def test_write_passes_its_findings_into_the_page(monkeypatch: Any, tmp_path: Any) -> None:
    """Breaks if `write` builds the overview without the findings it holds."""
    design, _field1, _field2 = _system_design(fransys_parts.load("demo_parts"))
    result = fr.build(fransys_parts.load("demo_parts"), design.draft())
    known = _finding(Severity.WARNING)
    seen: dict[str, Any] = {}

    def spy(*_args: Any, findings: Any = (), **_kwargs: Any) -> dict[str, bytes]:
        seen["findings"] = findings
        return {}

    monkeypatch.setattr(pipeline, "_raw_findings", lambda *_: (known,))
    monkeypatch.setattr(pipeline, "_exports", spy)
    fr.write(result, tmp_path)
    assert seen["findings"] == (known,)


def test_a_large_count_is_printed_in_full() -> None:
    """Breaks if the count is capped (for example to 99+) before it reaches the page data."""
    item = overview_graph(_laid()[0]).nodes[0].item
    data = _page(*(_finding(Severity.INFO, item) for _ in range(121)))
    view, box = _view_with(data, "item", 0)
    assert _flags(data, view)[box] == ["info", 121]


def test_the_badge_is_a_pill_that_grows_with_its_label() -> None:
    """Breaks if the badge goes back to a fixed-size ellipse or the count gets a cap."""
    text = html(
        _laid()[0], findings=(_finding(Severity.ERROR, overview_graph(_laid()[0]).nodes[0].item),)
    )
    rule = re.search(r"selector: 'node\[role=\"badge\"\]', style: \{(.*?)\} \}", text, re.DOTALL)
    assert rule is not None
    assert "'round-rectangle'" in rule.group(1)
    assert "width: 'data(w)'" in rule.group(1)
    assert "ellipse" not in rule.group(1)
    assert "label.length" in text
    assert "99+" not in text
