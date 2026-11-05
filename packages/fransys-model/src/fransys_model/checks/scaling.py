"""Validator: a channel's engineering range is ordered, named and on an analogue channel (R1753, model-0425)."""

from typing import TYPE_CHECKING, Final

from fransys_model.checks._finding import ordered
from fransys_model.derive.facts.plc_wiring import plc_requests
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
SCALING_UNIT_EMPTY: Final[str] = "SCALING_UNIT_EMPTY"
_ANALOGUE: Final[frozenset[SignalType]] = frozenset(
    {SignalType.AI_CURRENT, SignalType.AI_VOLTAGE, SignalType.AO_CURRENT, SignalType.AO_VOLTAGE, SignalType.RTD}
)


def _findings(scale: ScalingFacet, *, analogue: bool) -> list[Finding]:
    """The findings of one `ScalingFacet`; `analogue` says its function requests an analogue signal."""
    who, subjects = ref(scale.subject), (scale.id, scale.subject)
    found: list[Finding] = []
    if scale.eng_min >= scale.eng_max or scale.raw_min >= scale.raw_max:
        msg = f"the range of {who} is not low to high: raw {scale.raw_min}..{scale.raw_max}, eng {scale.eng_min}..{scale.eng_max}; "
        msg += "write the low value first"
        found.append(finding(SCALING_RANGE_INVALID, subjects, msg))
    text = scale.unit
    if not text.strip() or "\n" in text:
        found.append(finding(SCALING_UNIT_EMPTY, subjects, f'the unit of {who} is blank or has several lines; name the unit, e.g. "%" or "bar"'))
    if not analogue:
        msg = f"{who} is scaled but is not an analogue channel; request it with fr.AI, fr.AO or fr.SignalType.RTD"
        found.append(finding(SCALING_NOT_ANALOGUE, subjects, msg))
    return found


def check_scaling(model: Model) -> tuple[Finding, ...]:
    """Check each `ScalingFacet`; `SCALING_RANGE_INVALID`, `SCALING_NOT_ANALOGUE` and `SCALING_UNIT_EMPTY` (`ERROR`)."""
    requests = plc_requests(model)
    return ordered(
        [
            found
            for scale in facets_of(model, ScalingFacet).values()
            for found in _findings(scale, analogue=scale.subject in requests and requests[scale.subject].signal in _ANALOGUE)
        ]
    )
