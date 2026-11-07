"""Validator: a channel's engineering range is ordered and on an analogue channel (R1753, model-0425, R1824)."""

from typing import TYPE_CHECKING, Final

from fransys_model.checks._finding import ordered
from fransys_model.derive.facts.plc_wiring import plc_requests
from fransys_model.derive.facts.roles import function_channel
from fransys_model.vocab.codes import finding
from fransys_model.vocab.enums import SignalType
from fransys_model.vocab.facets.scaling import ScalingFacet
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import facets_of
lazy from fransys_model.kernel import Finding

if TYPE_CHECKING:
    from fransys_model.kernel import Model

# SCALING-UNIT-TYPED (KI-681): the unit is a free string until elecdef `Unit` carries every unit an engineer prints.
SCALING_RANGE_INVALID: Final[str] = "SCALING_RANGE_INVALID"
SCALING_NOT_ANALOGUE: Final[str] = "SCALING_NOT_ANALOGUE"
_ANALOGUE: Final[frozenset[SignalType]] = frozenset(
    {SignalType.AI_CURRENT, SignalType.AI_VOLTAGE, SignalType.AO_CURRENT, SignalType.AO_VOLTAGE, SignalType.RTD}
)


def _findings(scale: ScalingFacet, *, analogue: bool) -> list[Finding]:
    """The findings of one `ScalingFacet`; `analogue` says the function it scales is an analogue channel or requests one."""
    who, subjects = ref(scale.subject), (scale.id, scale.subject)
    found: list[Finding] = []
    if scale.eng_min >= scale.eng_max or scale.raw_min >= scale.raw_max:
        msg = f"the range of {who} is not low to high: raw {scale.raw_min}..{scale.raw_max}, eng {scale.eng_min}..{scale.eng_max}; "
        msg += "write the low value first"
        found.append(finding(SCALING_RANGE_INVALID, subjects, msg))
    if not analogue:
        msg = f"{who} is scaled but is not an analogue channel; request it with fr.AI, fr.AO or fr.SignalType.RTD"
        found.append(finding(SCALING_NOT_ANALOGUE, subjects, msg))
    return found


def check_scaling(model: Model) -> tuple[Finding, ...]:
    """Check each `ScalingFacet`; `SCALING_RANGE_INVALID` and `SCALING_NOT_ANALOGUE` (`ERROR`).

    The signal is the requesting function's: the request's, else a spare channel function's own.
    """
    requests = plc_requests(model)
    found = []
    for scale in facets_of(model, ScalingFacet).values():
        channel = function_channel(model, scale.subject)
        request = requests.get(scale.subject)
        signal = channel.signal if channel is not None else None if request is None else request.signal
        found += _findings(scale, analogue=signal in _ANALOGUE)
    return ordered(found)
