"""Vocabulary: a supply system and its rails (decision model-0075)."""

from decimal import Decimal

from fransys_model.kernel import AuthoringKey, Id, SchemaError, Value, record, value

from .core import Port, Unit
from .enums import Current, Earthing

PHASE_STEP = 60


@value
class Rail:
    """One rail of a supply system: the highest voltage to earth and, for AC, the phase.

    Example: `Rail(max_v=Decimal("230"), phase=120)` is phase L2 of a 400 V system;
    `Rail(max_v=Decimal("24"), phase=None)` is the `+24V` rail of a DC one. `max_v` is the
    RMS phase-to-earth value for AC and the potential against the supply's reference for DC,
    which may be negative. `phase` is in degrees and is `None` for DC and for an AC rail at
    0 V. `Rail` checks nothing itself; the `SupplySystem` that holds it applies
    `rail_phase_problem` (an AC rail above 0 V has a phase, every phase is a multiple of 60).
    """

    max_v: Decimal
    phase: int | None


def rail_phase_problem(current: Current, rail: Rail) -> str | None:
    """Why `rail` breaks the phase rule of a supply of `current`, or `None` if it does not.

    The one home of the rule: `SupplySystem` refuses a rail with a problem and authoring
    calls this before it builds the record. It is type-tolerant: a `current`, `max_v` or `phase`
    of the wrong type gives `None`, because `freeze()` reports the type.
    """
    max_v, phase = rail.max_v, rail.phase
    if type(current) is not Current or type(max_v) is not Decimal:  # ty: ignore[redundant-condition-strict] -- type tolerance, see docstring
        return None
    if phase is None:
        if current is Current.AC and max_v != 0:
            return f"is AC at {max_v} V and needs a phase"
        return None
    if type(phase) is int and phase % PHASE_STEP != 0:
        return f"phase must be a multiple of {PHASE_STEP} degrees, not {phase}"
    return None


@record(kind="supply_system")
class SupplySystem:
    """A named supply with its rails, a plant fact beside `Net`.

    Example: `SupplySystem(name="400V", current=Current.AC, rails=...)` holds rails `L1`,
    `L2`, `L3` and `N`, each named as `Net.potential` names it. Protective earth is not a
    supplied rail: a rail carried by a `PE`-class net is earth, at 0 V to earth in every supply.
    `earthing` says how the source is earthed. `fault_current_a` is the supply's prospective
    current into a bolted fault, `fault_time_constant_ms` its DC time constant (RATINGS-3 R3).
    `unit` is the unit that declares it, as `Item.unit` is; `pins` are the ports its call puts
    its rails on, sorted by id (RATINGS-3 R6).
    Not a `Part`, not an `Item`: it has no designation and no place.
    """

    id: Id[SupplySystem]
    key: AuthoringKey
    name: str
    current: Current
    earthing: Earthing = Earthing.EARTHED
    rails: frozendict[str, Rail] = frozendict()
    fault_current_a: Decimal | None = None
    fault_time_constant_ms: Decimal | None = None
    unit: Id[Unit] | None = None
    pins: tuple[Id[Port], ...] = ()
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Refuse a rail that breaks the phase rule, in potential order (`rail_phase_problem`).

        Rails that are not a `frozendict` of `str` to `Rail` are left as they are: `freeze()`
        reports them.
        """
        rails = self.rails
        if type(rails) is not frozendict:
            return
        for potential in sorted(key for key in rails if type(key) is str):
            rail = rails[potential]
            if type(rail) is not Rail:
                continue
            problem = rail_phase_problem(self.current, rail)
            if problem is not None:
                msg = f"supply system {self.name!r} rail {potential!r} {problem}"
                holder = self.id if type(self.id) is Id else None
                raise SchemaError(msg, kind="supply_system", record_id=holder)
