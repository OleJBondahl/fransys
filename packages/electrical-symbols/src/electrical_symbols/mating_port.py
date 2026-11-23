"""The port on a pin cell's and a mating cell's mating edge: code that counts ports as pins skips it."""

_MATING_PORT = "mate"


def is_mating_port(port_id: str) -> bool:
    """Whether `port_id` (`mate`, or `<k>.mate` in a table) is a mating edge's port and no pin."""
    return port_id.rsplit(".", 1)[-1] == _MATING_PORT
