"""Vocabulary: the value types of a rating and of an operating envelope (decision model-0079)."""

from decimal import Decimal

from fransys_model.kernel import value


@value
class BreakingPoint:
    """One point a protective device breaks: a voltage and the current it breaks there.

    Example: `BreakingPoint(voltage_v=Decimal("250"), current_a=Decimal("10000"))` is a fuse
    that breaks 10 kA at 250 V. `time_constant_ms` is the circuit's L/R time constant and is
    stated on a DC point only. The model guarantees the types only.
    """

    voltage_v: Decimal
    current_a: Decimal
    time_constant_ms: Decimal | None = None


@value
class Rating:
    """What a function or a part is rated for; a field is `None` when the datasheet says nothing.

    Example: `Rating(voltage_ac_v=Decimal("250"), current_ac_a=Decimal("0.5"))` is a contact
    rated 250 V AC and 0.5 A AC, with no DC rating. Voltages are RMS for AC and the highest
    permissible potential for DC; currents are the continuous rating, except
    `min_breaking_current_a`, the lowest current a partial-range fuse breaks. The model
    guarantees the types only; comparing a rating with what the plant does is a check's job.
    """

    voltage_ac_v: Decimal | None = None
    voltage_dc_v: Decimal | None = None
    current_ac_a: Decimal | None = None
    current_dc_a: Decimal | None = None
    min_breaking_current_a: Decimal | None = None
    power_loss_w: Decimal | None = None
    breaking_ac: tuple[BreakingPoint, ...] = ()
    breaking_dc: tuple[BreakingPoint, ...] = ()
    # `breaking_ac` and `breaking_dc` are the points a protective device breaks, each a voltage
    # and a breaking current (RATINGS-3 R1).
    # `min_breaking_current_a` (decision model-0088) is set on a partial-range fuse only: the
    # lowest current it breaks. Its presence alone marks the protective device partial-range,
    # which bounds no continuous current.
    # `power_loss_w` (spec F8) is the heat given off at the rated load, above 0 in a rating. A later
    # heat sum reads the part's own rating once and each template's rating, and never
    # `effective_rating`, which hands the part's rating to every function without one.


@value
class Operating:
    """What a function needs to run and what it is allowed to see; a field is `None` if unknown.

    Example: `Operating(nominal_voltage_v=Decimal("24"), min_voltage_v=Decimal("18"),
    max_voltage_v=Decimal("30"))` is a 24 V DC input that works from 18 V to 30 V;
    `capacity_ah` is set on a battery only. `voltage_ac_v` and `voltage_dc_v` are the supply
    the function is built for, `nominal_voltage_v` the value it is specified at, and
    `min_voltage_v`/`max_voltage_v` the window it operates in. The model guarantees the types
    only. `max_current_ac_a` and `max_current_dc_a` are a source's
    continuous current limit, the most that flows through it in either direction, charging
    included; they bound the branch the source sits on.
    `resistance_ohm`, `nominal_power_w` and `nominal_current_a` are each stated at
    `nominal_voltage_v`; only `nominal_current_a`, a load's draw, is read. `fault_current_ac_a`
    and `fault_current_dc_a` are a source's prospective current into a bolted fault,
    `fault_time_constant_ms` the DC time constant (RATINGS-3 R2).
    """

    voltage_ac_v: Decimal | None = None
    voltage_dc_v: Decimal | None = None
    nominal_voltage_v: Decimal | None = None
    max_voltage_v: Decimal | None = None
    min_voltage_v: Decimal | None = None
    capacity_ah: Decimal | None = None
    max_current_ac_a: Decimal | None = None
    max_current_dc_a: Decimal | None = None
    resistance_ohm: Decimal | None = None
    nominal_power_w: Decimal | None = None
    nominal_current_a: Decimal | None = None
    fault_current_ac_a: Decimal | None = None
    fault_current_dc_a: Decimal | None = None
    fault_time_constant_ms: Decimal | None = None


def effective_rating(template: Rating | None, part: Rating | None) -> Rating | None:
    """The rating a function has: its template's when it has one, else its part's.

    The one place of the rule; the readers, the checks and the authoring read all call it.
    The template's `Rating` replaces the part's whole, never field by field: a template rating
    with only `voltage_ac_v` hides the part's `voltage_dc_v`, so the result's `voltage_dc_v` is
    `None`. `None` when neither is given.
    """
    return template if template is not None else part
