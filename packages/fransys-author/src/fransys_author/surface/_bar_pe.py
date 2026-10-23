"""A bar's screw joins the PE net, however it is reached: next free, or named (PE-BAR B2)."""

from typing import TYPE_CHECKING

from fransys_author._earth_net import earth_net
from fransys_author._keys import scoped
from fransys_author._origin import caller_origin

if TYPE_CHECKING:
    from fransys_author.handles import Fn, Port


def join_pe(fn: Fn, screw: Port) -> None:
    """A one-port `PE` net per screw: one net of a name per scope would conflict on the next."""
    net = earth_net(scoped(screw.key, "pe"), (screw.id,))
    fn._recorder._add(net, caller_origin())
