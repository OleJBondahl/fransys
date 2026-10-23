"""The one shape of a `PE` net: every author site that declares one builds it here."""

from typing import TYPE_CHECKING

from fransys_model.kernel import make_id
from fransys_model.vocab import Net, NetClass

if TYPE_CHECKING:
    from fransys_model.kernel import AuthoringKey, Id
    from fransys_model.vocab import Port


def earth_net(key: AuthoringKey, ports: tuple[Id[Port], ...]) -> Net:
    """The `PE` net under `key` that joins `ports`, with no potential of its own."""
    return Net(
        id=make_id(Net, key),
        key=key,
        name="PE",
        net_class=NetClass.PE,
        ports=ports,
        potential=None,
    )
