"""A bar's screw joins the PE net, however it is reached: next free, or named (PE-BAR B2)."""

from typing import TYPE_CHECKING

from fransys_author._keys import scoped
from fransys_author._origin import caller_origin
from fransys_model.kernel import make_id
from fransys_model.vocab import Net, NetClass

if TYPE_CHECKING:
    from fransys_author.handles import Fn, Port


def join_pe(fn: Fn, screw: Port) -> None:
    """A one-port `PE` net per screw: one net of a name per scope would conflict on the next."""
    key = scoped(screw.key, "pe")
    net = Net(
        id=make_id(Net, key),
        key=key,
        name="PE",
        net_class=NetClass.PE,
        ports=(screw.id,),
        potential=None,
    )
    fn._recorder._add(net, caller_origin())
