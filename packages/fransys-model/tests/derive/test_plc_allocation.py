"""WP15 tests: `derive.passes.plc_allocation` (ROADMAP WP15, design/connectivity.md,
design/facets.md, design/derive.md).

Priority is ascending: `priority=1` is served before `priority=2` (design/derive.md).
"""

from derive_helpers import add_all

from fransys_model.derive.passes.plc_allocation import PLC_REQUEST_UNSERVABLE, allocate_plc
from fransys_model.kernel import Draft, Id, Origin, freeze
from fransys_model.vocab.core import Function, Item
from fransys_model.vocab.enums import FunctionKind, PartCategory, SignalType
from fransys_model.vocab.facets.plc import PlcBindingFacet, PlcChannelFacet, PlcRequestFacet
from fransys_model.vocab.tables import facets_of
from fransys_model.vocab.templates import FunctionTemplate, Part

_RACK_PART = Part(
    id=Id(kind="part", value="1" * 32),
    key=("rack",),
    mpn="SIM-RACK-8",
    manufacturer="Synthetic Parts Co",
    description="8-slot PLC rack",
    category=PartCategory.PLC_MODULE,
    class_code="A",
)


def _di_module(value: str, key: tuple[str, ...], *, channel_count: int, position: int = 1):
    module_part = Part(
        id=Id(kind="part", value=value * 32),
        key=(*key, "part"),
        mpn="SIM-DI8-024",
        manufacturer="Synthetic Parts Co",
        description="8ch 24V digital input module",
        category=PartCategory.PLC_MODULE,
        class_code="A",
    )
    channel_templates = tuple(
        FunctionTemplate(
            id=Id(kind="function_template", value=f"{value}{n}".ljust(32, "0")),
            key=(*key, "part", f"ch_{n}"),
            part=module_part.id,
            name=f"ch_{n}",
            kind=FunctionKind.PLC_CHANNEL,
        )
        for n in range(1, channel_count + 1)
    )
    channel_facets = tuple(
        PlcChannelFacet(
            id=Id(kind="facet.plc_channel", value=f"{value}{n}".ljust(32, "0")),
            key=(*key, "part", f"ch_{n}", "facet"),
            subject=template.id,
            signal=SignalType.DI,
            channel=n,
        )
        for n, template in enumerate(channel_templates, start=1)
    )
    module_item = Item(
        id=Id(kind="item", value=value * 32),
        key=key,
        part=module_part.id,
        parent=None,
        position=position,
        tag="A1-1",
        description="digital input module",
    )
    channel_functions = tuple(
        Function(
            id=Id(kind="function", value=f"{value}f{n}".ljust(32, "0")),
            key=(*key, f"ch_{n}"),
            item=module_item.id,
            template=template.id,
            name=f"ch_{n}",
            kind=FunctionKind.PLC_CHANNEL,
        )
        for n, template in enumerate(channel_templates, start=1)
    )
    return module_part, channel_templates, channel_facets, module_item, channel_functions


def _field_device(value: str, key: tuple[str, ...], *, signal: SignalType, priority: int):
    item = Item(
        id=Id(kind="item", value=value * 32),
        key=key,
        part=None,
        parent=None,
        position=None,
        tag=None,
        description="field device",
    )
    function = Function(
        id=Id(kind="function", value=(value + "f").ljust(32, "0")),
        key=(*key, "signal"),
        item=item.id,
        template=None,
        name="signal",
        kind=FunctionKind.SENSOR,
    )
    request = PlcRequestFacet(
        id=Id(kind="facet.plc_request", value=(value + "r").ljust(32, "0")),
        key=(*key, "signal", "request"),
        subject=function.id,
        signal=signal,
        signal_name=f"tag_{value}",
        priority=priority,
    )
    return item, function, request


def test_allocate_plc_is_deterministic_under_shuffling(origin: Origin) -> None:
    """Allocating two equal-priority requests against two channels is order-independent."""
    module_part, templates, facets, module_item, channels = _di_module(
        "5", ("a1",), channel_count=2
    )
    item_a, func_a, req_a = _field_device("a", ("dev-a",), signal=SignalType.DI, priority=1)
    item_b, func_b, req_b = _field_device("b", ("dev-b",), signal=SignalType.DI, priority=1)

    common = (_RACK_PART, module_part, *templates, *facets, module_item, *channels)
    forward = Draft()
    add_all(forward, *common, item_a, func_a, req_a, item_b, func_b, req_b, origin=origin)
    backward = Draft()
    add_all(backward, *common, item_b, func_b, req_b, item_a, func_a, req_a, origin=origin)

    forward_model, _ = allocate_plc(freeze(forward))
    backward_model, _ = allocate_plc(freeze(backward))
    assert forward_model.digest == backward_model.digest


def test_allocate_plc_respects_priority(origin: Origin) -> None:
    """With one free channel and two requests, the `priority=1` request wins it."""
    module_part, templates, facets, module_item, channels = _di_module(
        "2", ("a2",), channel_count=1
    )
    item_a, func_a, req_a = _field_device("c", ("dev-c",), signal=SignalType.DI, priority=2)
    item_b, func_b, req_b = _field_device("d", ("dev-d",), signal=SignalType.DI, priority=1)

    draft = Draft()
    add_all(
        draft,
        _RACK_PART,
        module_part,
        *templates,
        *facets,
        module_item,
        *channels,
        item_a,
        func_a,
        req_a,
        item_b,
        func_b,
        req_b,
        origin=origin,
    )
    model, findings = allocate_plc(freeze(draft))

    bindings = facets_of(model, PlcBindingFacet)
    bound_subjects = {b.subject for b in bindings.values()}
    assert func_b.id in bound_subjects
    assert func_a.id not in bound_subjects
    assert any(f.code == PLC_REQUEST_UNSERVABLE and func_a.id in f.subjects for f in findings)


def test_allocate_plc_never_double_books_a_channel(origin: Origin) -> None:
    """A channel that already has a binding never receives a second one."""
    module_part, templates, facets, module_item, channels = _di_module(
        "3", ("a3",), channel_count=1
    )
    item_a, func_a, req_a = _field_device("e", ("dev-e",), signal=SignalType.DI, priority=1)
    item_b, func_b, req_b = _field_device("f", ("dev-f",), signal=SignalType.DI, priority=1)

    draft = Draft()
    add_all(
        draft,
        _RACK_PART,
        module_part,
        *templates,
        *facets,
        module_item,
        *channels,
        item_a,
        func_a,
        req_a,
        item_b,
        func_b,
        req_b,
        origin=origin,
    )
    model, _findings = allocate_plc(freeze(draft))

    bindings = facets_of(model, PlcBindingFacet)
    channel_ids = [b.channel for b in bindings.values()]
    assert len(channel_ids) == len(set(channel_ids))


def test_allocate_plc_unservable_request_gets_finding_and_no_binding(origin: Origin) -> None:
    """A request whose signal type no channel provides gets a finding, never a binding."""
    module_part, templates, facets, module_item, channels = _di_module(
        "4", ("a4",), channel_count=1
    )
    item, func, req = _field_device("g", ("dev-g",), signal=SignalType.RTD, priority=1)

    draft = Draft()
    add_all(
        draft,
        _RACK_PART,
        module_part,
        *templates,
        *facets,
        module_item,
        *channels,
        item,
        func,
        req,
        origin=origin,
    )
    model, findings = allocate_plc(freeze(draft))

    bindings = facets_of(model, PlcBindingFacet)
    assert func.id not in {b.subject for b in bindings.values()}
    assert any(f.code == PLC_REQUEST_UNSERVABLE and func.id in f.subjects for f in findings)
