"""What `Fn.plc` and `Fn.scale` refuse at the call: a channel's settings and a device's request (WAGO-CDP, R1824)."""

from typing import TYPE_CHECKING, cast

from fransys_model.kernel import make_id
from fransys_model.vocab import PlcRequestFacet, ScalingFacet

from ._keys import scoped
from .errors import AuthorError

if TYPE_CHECKING:
    from fransys_model.vocab import Function

    from .handles import Fn, _Recorder

_UNCONFIGURED = "an unconfigured channel carries nothing: drop the {what}, or leave the channel configured"


def _is_channel(recorder: _Recorder, fn: Fn) -> bool:
    """Whether `fn` is a function of a PLC module's channel template."""
    template = cast("Function", recorder._draft.record_of(fn.id)).template
    return template in recorder._catalogue.plc_channels


def _scaled(recorder: _Recorder, fn: Fn) -> bool:
    """Whether `fn` carries a scaling."""
    return recorder._draft.key_of(make_id(ScalingFacet, scoped(fn.key, "scaling"))) is not None


def _refuse_device_plc(fn: Fn, facet: PlcRequestFacet) -> None:
    """Raise `AuthorError` for a `.plc` call on a device function that is no request."""
    if facet.signal is None or facet.signal_name is None:
        msg = f"{fn.name} is a device function: it asks for a channel by its signal and name, as .plc(fr.DI, 'door-closed')"
        raise AuthorError(msg)
    if not facet.configured:
        msg = f"{fn.name} is no channel of a PLC module: configured=False belongs on a module's channel, as module.di_1.plc(configured=False)"
        raise AuthorError(msg)


def refuse_plc(recorder: _Recorder, fn: Fn, facet: PlcRequestFacet) -> None:
    """Raise `AuthorError` for a `.plc` call that a device or a module's channel cannot take."""
    if not _is_channel(recorder, fn):
        _refuse_device_plc(fn, facet)
        return
    if facet.signal is not None:
        msg = f"{fn.name} is a channel of its module and has its signal already: write .plc(name=...) to name it"
        raise AuthorError(msg)
    if not facet.configured:
        what = "name" if facet.signal_name is not None else "routing" if facet.routing is not None else "scale" if _scaled(recorder, fn) else ""
        if what:
            raise AuthorError(_UNCONFIGURED.format(what=what))


def refuse_scale(recorder: _Recorder, fn: Fn, unit: str | None) -> None:
    """Raise `AuthorError` for a blank unit, or a scale on a channel left out with `configured=False`."""
    if unit is not None and (not unit.strip() or "\n" in unit):
        msg = 'a unit is text on one line: name it, e.g. "%" or "bar", or leave it out for no unit'
        raise AuthorError(msg)

    settings = recorder._draft.record_of(make_id(PlcRequestFacet, scoped(fn.key, "plc_request")))
    if isinstance(settings, PlcRequestFacet) and not settings.configured:
        raise AuthorError(_UNCONFIGURED.format(what="scale"))
