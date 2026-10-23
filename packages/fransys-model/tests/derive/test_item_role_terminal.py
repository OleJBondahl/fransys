"""`ItemRole.terminal` reproduces every `ItemKind.TERMINAL` branch (EL-3 RR) over demo parts.

The oracle is the old test, `item_kind(..) is ItemKind.TERMINAL`, read at the three sites:
`kinds.py` (`terminal_items`), `marker_targets.py` (a terminal first) and `page_nav.py`
(the outline entry rule, gone with the outline entries).
"""

import fransys as fr
import pytest
from fransys.colours import BU

from fransys_model.derive import ItemKind, item_kind, item_role
from fransys_model.derive.facts.item_predicates import terminal_items
from fransys_model.vocab.roles import ITEM_ROLES
from fransys_model.vocab.tables import items


@pytest.fixture(scope="module")
def model() -> fr.Model:
    """A strip of three terminals, a breaker and a two-pin connector, wired to the strip."""
    d = fr.design("demo_parts")
    d.location("L0", "Workshop")
    with d.function("T", "Terminals"):
        strip = d.terminal_strip("X1", "DEMO-TB-2.5", 3)
        cb = d.device("CB", "DEMO-MCB-3P", place="L0")
        cn = d.device("CN", "DEMO-CONN-2P", place="L0")
        d.detail.wire(cb[1], cn[1], wire=(BU, 0.5))
        d.detail.wire(cb[2], strip[1], wire=(BU, 0.5))
    return fr.build(d).model


def test_the_flag_is_the_terminal_branch_on_every_item(model: fr.Model) -> None:
    """Catches a row that sets `terminal` on another kind or misses the terminal kind."""
    found = {item_kind(model, i) for i in items(model)}
    assert {ItemKind.TERMINAL, ItemKind.STRIP, ItemKind.DEVICE} <= found
    for item in items(model):
        assert item_role(model, item).terminal == (item in terminal_items(model))
        assert item_role(model, item).terminal == (item_kind(model, item) is ItemKind.TERMINAL)


def test_only_the_terminal_row_sets_the_flag() -> None:
    """Catches a second kind carrying `terminal` in the table."""
    assert [k for k, r in ITEM_ROLES.items() if r.terminal] == [ItemKind.TERMINAL]
