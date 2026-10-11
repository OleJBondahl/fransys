"""`lint.members.check_nowhere`: a net drawn nowhere is `CONNECTION_NOT_DRAWN` (layout-0080).

`check_members` lets a `(port, set)` pair in `exempt` draw nothing. The guard is the net under
that: a net of two or more ports with a member placed in some set and no route end or marker on
any of its members, in any set, is one finding, subjects its placed member ports. Every case has
a twin that must stay silent. All data is invented.

Function `n` has ports `10n + 1` and `10n + 2`; the net here is ports 12 and 21 (and 31).
"""

from coherence_helpers import DRAWN, layout_of, named, port
from samples import connection, placed

from fransys_layout.lint.codes import CONNECTION_NOT_DRAWN
from fransys_layout.lint.members import check_members, check_nowhere
from fransys_model.kernel import Severity

C1 = connection(1, 1, 2)  # port 12 to port 21
FUNCTIONS = (placed(1, x=104, y=96, page=1), placed(2, x=104, y=304, page=1))
NOWHERE = [(CONNECTION_NOT_DRAWN, (port(12), port(21)))]
EXEMPT_BOTH = frozenset({(port(12), 1), (port(21), 1)})
GOOD = ((104, 112), (104, 288))


def _nowhere(*, routes=(), markers=(), functions=FUNCTIONS, connections=(C1,), groups=()):
    layout = layout_of(routes=routes, markers=markers, functions=functions)
    return check_nowhere(layout, connections, groups, DRAWN)


def test_a_net_whose_placed_members_are_all_exempt_and_bare_is_drawn_nowhere() -> None:
    """Both ports are exempt in set 1 (the members check is silent) and nothing covers them.

    # UNDO: lint/members.py, `check_nowhere` returns nothing (delete the guard)
    """
    layout = layout_of(functions=FUNCTIONS)
    assert check_members(layout, (C1,), (), DRAWN, EXEMPT_BOTH) == ()
    found = check_nowhere(layout, (C1,), (), DRAWN)
    assert named(found) == NOWHERE
    assert found[0].severity is Severity.ERROR
