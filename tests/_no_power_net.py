"""One door for the F22 tests' "not a power net" claim (R467 Q21, R478)."""

from fransys_model.derive import port_power_kind
from fransys_model.vocab import PowerKind
from fransys_model.vocab.tables import ports

__all__ = ["assert_no_power_net"]


def assert_no_power_net(model) -> None:
    """Every port of `model` stands on a net `derive.port_power_kind` calls `NONE`.

    Q21 sends a power net to POWER-NET; a fan-out test of the trunk shape holds only while
    no net of its fixture is one.
    """
    assert len(ports(model)) > 0
    assert {port_power_kind(model, port) for port in ports(model)} == {PowerKind.NONE}
