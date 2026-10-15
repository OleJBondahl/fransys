"""model-0220: a terminal drawn by a copy still holds a harness line's end (TNR-SAME-PAGE-FIX).

In the narrow cabinet `-X2:1` is a star terminal, and cable `-W1` core 2 ends at it. The copies
step stands copies of `-X2:1` on other pages. The line's end finds the pin by the model's id, so
it must find the copy's pin too: an end with no pin on a page draws nothing there, and no
finding names the lost core.
"""

from collections import defaultdict

from layout_cabinet import build_cabinet
from narrow_cabinet import narrow_results

from fransys_layout.engines.schematic.read.harness_lines import line_reads
from fransys_layout.stages.wire_copies import copy_map
from fransys_model.derive.designation import port_designation
from fransys_model.kernel import freeze
from fransys_model.vocab.tables import ports

_NARROW_WIDTH_MM = 158


def _pages(designation: str) -> tuple[set[tuple[int, int]], set[tuple[int, int]]]:
    """The pages `designation`'s pin stands on, and those a line end there has a piece on."""
    model = freeze(build_cabinet())  # the narrow sheet changes no id
    at = defaultdict(set)
    for port in ports(model):
        at[port_designation(model, port)].add(port)
    mine = at[designation]
    functions = {ports(model)[port].function for port in mine}
    ends = {
        (line.owner, end.branch)
        for line in line_reads(model).lines
        for end in line.ends
        if set(end.ports) & mine
    }
    assert ends  # the cabinet has a line ending at that pin
    results = narrow_results(_NARROW_WIDTH_MM)[0]
    real = copy_map(results.copies)
    stands = {
        (one.drawing_set, one.page)
        for one in results.layout.placed
        if real.get(one.function, one.function) in functions
    }
    lines = results.lines
    pieces = [*lines.lines, *lines.fan_outs, *lines.stubs]
    drawn = {(one.drawing_set, one.page) for one in pieces if (one.harness, one.branch) in ends}
    return stands, drawn


def test_w1_core_2_is_drawn_on_every_page_a_copy_of_x2_1_stands_on() -> None:
    """`-X2:1` stands on pages 1, 3 and 5 (its home and two pages of copies): the end is on each."""
    stands, drawn = _pages("-X2:1")
    assert len(stands) > 1  # copies stand where the home does not
    assert stands <= drawn
