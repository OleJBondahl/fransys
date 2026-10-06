"""Fixtures of `test_ratings_acceptance_q5.py` (RATINGS-1 part 6, acceptance 5): units and supplies.

Unit `ub` has a 2-port connector `xb` (`DEMO-CONN-2P`) that is its boundary, stating a rating or
an operating envelope. Unit `ua` declares the supply `DC` (`+800` and `0V`) on its own connector
`xa`, whose ports are wired to `xb`'s. `ub` may hold a lamp behind `xb`. Demo parts only. The
tests folder is on `sys.path` (the test file inserts it) so `ratings_fixtures` imports by name.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

import fransys_parts
from fransys_author import Design
from ratings_fixtures import rated

from fransys_model.kernel import Id, Model, freeze, merge
from fransys_model.vocab.ratings import Operating, Rating

if TYPE_CHECKING:
    from fransys_model.vocab.core import Function


@dataclass(frozen=True, slots=True)
class Built:
    """A built model and the ids of the functions the tests ask about."""

    model: Model
    boundary_fn: Id[Function]
    lamp_fn: Id[Function] | None


def units_model(
    *,
    feed: bool = True,
    nested: bool = False,
    rating: Rating | None = None,
    operating: Operating | None = None,
    lamp_dc: str | None = None,
) -> Built:
    """Unit `ub` with its boundary `xb`; with `feed`, unit `ua` puts the 800 V / 0 V rails on `xb`.

    `nested` puts `ub` inside `ua`'s scope, else the two units stand side by side. `lamp_dc` adds
    a lamp `h1` in `ub`, wired to `xb`'s two ports and part-rated that many V DC.
    """
    library = fransys_parts.load("demo_parts")
    d = Design(library)
    wire = d.wiring(colour="BK", gauge="1.5")
    a = d.scope("a").unit("ua", revision=1, interface="1") if feed else None
    xa = None
    if a is not None:
        a.revision(1, date="2026-01-01", text="First release", created="XX")
        a.supply("DC", current="dc", rails={"+800": ("800", None), "0V": ("0", None)})
        xa = a.item("DEMO-CONN-2P", name="xa")
        a.net("+800", xa["1"], cls="power", potential="+800")
        a.net("0V", xa["2"], cls="power", potential="0V")
    home = a.scope("b") if a is not None and nested else d.scope("b")
    b = home.unit("ub", revision=1, interface="1")
    b.revision(1, date="2026-01-01", text="First release", created="XX")
    xb = b.item("DEMO-CONN-2P", name="xb")
    b.boundary(xb, rating=rating, operating=operating)
    if xa is not None:
        wire(xa["1"], xb["1"])
        wire(xa["2"], xb["2"])
    h1 = None
    if lamp_dc is not None:
        h1 = b.item("DEMO-LAMP-24", name="h1")
        wire(xb["1"], h1["1"])
        wire(xb["2"], h1["2"])
    model = freeze(merge(library, d.draft()))
    if lamp_dc is not None:
        model = rated(model, "DEMO-LAMP-24", "lamp", voltage_dc_v=lamp_dc)
    return Built(model, xb.fn("x1").id, None if h1 is None else h1.fn("lamp").id)


def dc(volts: str) -> Rating:
    """A DC-only `Rating` of `volts`."""
    return Rating(voltage_dc_v=Decimal(volts))


def two_earthed_supplies_model(lamp_ac: str) -> tuple[Model, Id[Function]]:
    """Earthed 230 V AC supplies `S1` (rail `L1`) and `S2` (rail `X1`), both at phase 0.

    A lamp `h1` stands across `L1` and `X1`, rated `lamp_ac` V AC (its template's rating). The
    second value is the lamp's function id.
    """
    library = fransys_parts.load("demo_parts")
    d = Design(library)
    d.supply("S1", current="ac", rails={"L1": ("230", 0)})
    d.supply("S2", current="ac", rails={"X1": ("230", 0)})
    lamp = d.item("DEMO-LAMP-24", name="h1")
    d.net("L1", lamp["1"], cls="power", potential="L1")
    d.net("X1", lamp["2"], cls="power", potential="X1")
    model = rated(freeze(merge(library, d.draft())), "DEMO-LAMP-24", "lamp", voltage_ac_v=lamp_ac)
    return model, lamp.fn("lamp").id
