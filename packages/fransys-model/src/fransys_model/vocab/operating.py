"""Vocabulary: what a function needs to run, for the figures elecdef has no home for (R783 Q3)."""

from elecdef import Quantity, Range

from fransys_model.kernel import value


@value
class Operating:
    """What a function needs to run and what it is allowed to see; a field is unset if unknown.

    Example: `Operating(voltage=(Range(Role.RATED, nom=Unit.V(24), min=Unit.V(18), max=Unit.V(30), at=At(Current.DC)),))`
    is a 24 V DC input that works from 18 V to 30 V. A voltage window is one `Range` with AC or DC in
    its `at`; `max_current` is a source's continuous limit, the most that flows through it in either
    direction, charging included, one `Range` per current kind; `fault_current` is its prospective
    current into a bolted fault, one `Range` per current kind, and `fault_time_constant` the DC time
    constant. `capacity` is set on a battery only. `resistance`, `nominal_power` and `nominal_current`
    are each stated at the nominal voltage; only `nominal_current`, a load's draw, is read.
    """

    voltage: tuple[Range, ...] = ()
    max_current: tuple[Range, ...] = ()
    fault_current: tuple[Range, ...] = ()
    fault_time_constant: Quantity | None = None
    capacity: Quantity | None = None
    resistance: Quantity | None = None
    nominal_power: Quantity | None = None
    nominal_current: Quantity | None = None
