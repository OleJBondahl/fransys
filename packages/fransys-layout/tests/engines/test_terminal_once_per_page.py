"""V4 (layout-0099): a terminal is drawn at most once per page, on the two-location cabinet."""

from collections import Counter

from layout_cabinet import build_cabinet

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_model.kernel import freeze
from fransys_model.vocab.tables import functions


def test_no_terminal_stands_twice_on_one_page_of_the_two_location_cabinet() -> None:
    model = freeze(build_cabinet(second_location=True))
    results, _ = stage_results(model, read_inputs(model))
    terminal = {f.id for f in functions(model).values() if f.key[-1] == "terminal"}
    count = Counter(
        (p.function, p.drawing_set, p.page) for p in results.layout.placed if p.function in terminal
    )
    assert count, "the cabinet draws no terminal: the test sees nothing"
    assert max(count.values()) == 1
