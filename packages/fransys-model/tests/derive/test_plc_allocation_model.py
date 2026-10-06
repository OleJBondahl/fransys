"""WP15 tests: what the allocation pass binds, keeps and reports (design/derive.md)."""

import dataclasses
import re
from typing import Any

import pytest
from plant import Plant

from fransys_model.derive.passes import plc_allocation
from fransys_model.derive.passes.plc_allocation import PLC_REQUEST_UNSERVABLE, allocate_plc
from fransys_model.kernel import Draft, Id, Model, Origin, Severity, freeze, make_id
from fransys_model.vocab.core import Function, Item, Unit
from fransys_model.vocab.enums import FunctionKind, PartCategory, SignalType
from fransys_model.vocab.facets.plc import PlcBindingFacet, PlcChannelFacet, PlcRequestFacet
from fransys_model.vocab.tables import facets_of
from fransys_model.vocab.templates import FunctionTemplate, Part
from fransys_model.vocab.validators.plc import check_plc


@dataclasses.dataclass(frozen=True)
class Slot:
    """Where a module sits: under which rack, in which position, installed or not."""

    rack: str | None = None
    position: int | None = None
    installed: bool = True
    unit: Id[Unit] | None = None


def _module(
    plant: Plant,
    name: str,
    *,
    signal: SignalType = SignalType.DI,
    channels: int = 2,
    where: Slot | None = None,
) -> list[Id[Function]]:
    """A module item with `channels` channel functions of `signal`, placed at `where`."""
    where = Slot() if where is None else where
    part = Part(
        id=make_id(Part, (name, "part")),
        key=(name, "part"),
        mpn=f"EXAMPLE-{name}",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.PLC_MODULE,
        class_code="A",
    )
    plant.add(part)
    parent = None
    if where.rack is not None:
        parent = make_id(Item, (where.rack,))
        if not plant.has(parent):
            plant.item(where.rack)
    module = Item(
        id=make_id(Item, (name,)),
        key=(name,),
        part=part.id,
        parent=parent,
        position=where.position,
        tag=None,
        description="Invented",
        installed=where.installed,
        unit=where.unit,
    )
    plant.add(module)
    functions = []
    for number in range(1, channels + 1):
        template = FunctionTemplate(
            id=make_id(FunctionTemplate, (name, "part", f"ch{number}")),
            key=(name, "part", f"ch{number}"),
            part=part.id,
            name=f"ch{number}",
            kind=FunctionKind.PLC_CHANNEL,
        )
        plant.add(
            template,
            PlcChannelFacet(
                id=make_id(PlcChannelFacet, (name, str(number), "facet")),
                key=(name, str(number), "facet"),
                subject=template.id,
                signal=signal,
                channel=number,
            ),
        )
        functions.append(plant.function(module.id, f"ch{number}", template=template.id))
    return functions


def _request(
    plant: Plant, name: str, signal: SignalType = SignalType.DI, *, priority: int = 1
) -> Id[Function]:
    function = plant.function(plant.item(name), "signal")
    plant.add(
        PlcRequestFacet(
            id=make_id(PlcRequestFacet, (name, "signal", "request")),
            key=(name, "signal", "request"),
            subject=function,
            signal=signal,
            signal_name=f"tag_{name}",
            priority=priority,
        )
    )
    return function


def _bound(model: Model) -> dict[Id[Function], Id[Function]]:
    return {b.subject: b.channel for b in facets_of(model, PlcBindingFacet).values()}


def _run(plant: Plant) -> tuple[dict[Id[Function], Id[Function]], tuple[Any, ...]]:
    model, findings = allocate_plc(plant.model())
    return _bound(model), findings


# ---- request order ------------------------------------------------------------------------


def test_the_lower_priority_number_is_served_first() -> None:
    """One channel, two requests: `priority=1` wins it, `priority=2` is unservable."""
    plant = Plant()
    (channel,) = _module(plant, "m1", channels=1)
    late = _request(plant, "a-late", priority=2)
    early = _request(plant, "z-early", priority=1)
    bound, findings = _run(plant)
    assert bound == {early: channel}
    assert [f.subjects for f in findings] == [
        tuple(sorted((make_id(PlcRequestFacet, ("a-late", "signal", "request")), late)))
    ]


def test_equal_priorities_are_served_in_the_requesting_functions_key_order() -> None:
    """Keys, not ids and not insertion order: `dev-a` gets the first channel."""
    plant = Plant()
    first, second = _module(plant, "m1", channels=2)
    b = _request(plant, "dev-b")
    a = _request(plant, "dev-a")
    assert _run(plant)[0] == {a: first, b: second}


def test_a_priority_beats_a_key() -> None:
    """A later key with a smaller priority number still goes first."""
    plant = Plant()
    first, second = _module(plant, "m1", channels=2)
    a = _request(plant, "dev-a", priority=5)
    z = _request(plant, "dev-z", priority=1)
    assert _run(plant)[0] == {z: first, a: second}


# ---- channel order ------------------------------------------------------------------------


def _first_channel(plant: Plant) -> Id[Function]:
    request = _request(plant, "dev")
    return _run(plant)[0][request]


def test_channels_are_served_by_rack_then_position_then_module_then_channel_number() -> None:
    """The key ranks the racks; the ids and the insertion order rank nothing."""
    plant = Plant()
    _module(plant, "m-a1", where=Slot("rack-b", 1))
    wanted = _module(plant, "m-b9", where=Slot("rack-a", 1))
    assert _first_channel(plant) == wanted[0]


def test_within_a_rack_the_position_ranks_before_the_module_key() -> None:
    """Position 1 on module `z` beats position 2 on module `a`."""
    plant = Plant()
    _module(plant, "a", where=Slot("rack", 2))
    wanted = _module(plant, "z", where=Slot("rack", 1))
    assert _first_channel(plant) == wanted[0]


def test_a_module_without_a_position_sorts_after_every_positioned_one_of_its_rack() -> None:
    """`None` last."""
    plant = Plant()
    _module(plant, "a-unplaced", where=Slot("rack", None))
    wanted = _module(plant, "z-placed", where=Slot("rack", 7))
    assert _first_channel(plant) == wanted[0]


def test_equal_positions_fall_back_to_the_module_key() -> None:
    """Modules in one slot number: the keys decide, whatever the ids are."""
    plant = Plant()
    modules = {
        name: _module(plant, name, channels=1, where=Slot("rack", 1))
        for name in ("mod-d", "mod-b", "mod-c", "mod-a")
    }
    requests = [_request(plant, f"dev-{n}") for n in range(4)]
    bound = _run(plant)[0]
    assert [bound[r] for r in requests] == [
        modules[name][0] for name in ("mod-a", "mod-b", "mod-c", "mod-d")
    ]


def test_a_module_without_a_rack_sorts_before_any_rack() -> None:
    """The empty key is the smallest."""
    plant = Plant()
    _module(plant, "in-rack", where=Slot("rack-a", 1))
    wanted = _module(plant, "loose", where=Slot(position=9))
    assert _first_channel(plant) == wanted[0]


def test_channels_of_one_module_go_by_channel_number_not_by_function_id_or_key() -> None:
    """Channel 1 before channel 2, whatever the functions are called."""
    plant = Plant()
    channels = _module(plant, "m", channels=3)
    requests = [_request(plant, f"dev-{n}") for n in range(3)]
    bound = _run(plant)[0]
    assert [bound[r] for r in requests] == channels


def test_no_designation_is_read_so_an_unnumbered_rack_is_fine() -> None:
    """The order is by key: racks and modules have `designation=None` throughout."""
    plant = Plant()
    wanted = _module(plant, "m", where=Slot("rack"))
    request = _request(plant, "dev")
    bound, findings = _run(plant)
    assert bound == {request: wanted[0]}
    assert findings == ()


# ---- the serving unit -----------------------------------------------------------------------


def test_serving_falls_all_the_way_up_a_multi_level_unit_chain() -> None:
    """Only the top level declares DI; a grandchild's queue is still found there."""
    plant = Plant()
    top = plant.unit("top")
    child = plant.unit("child", parent=top)
    grand = plant.unit("grand", parent=child)
    _module(plant, "m", where=Slot(unit=top))
    model = plant.model()
    ranked = plc_allocation._ranked(model)
    channels = plc_allocation._channels(model, ranked)
    assert plc_allocation._serving(model, grand, SignalType.DI, channels) == (top, SignalType.DI)


def test_serving_falls_back_to_its_own_key_when_the_chain_declares_nothing() -> None:
    """Neither a real unit's chain nor the top level declares a signal none of them has."""
    plant = Plant()
    top = plant.unit("top")
    child = plant.unit("child", parent=top)
    grand = plant.unit("grand", parent=child)
    _module(plant, "m", where=Slot(unit=top))  # declares DI only
    model = plant.model()
    ranked = plc_allocation._ranked(model)
    channels = plc_allocation._channels(model, ranked)
    assert plc_allocation._serving(model, grand, SignalType.AI_CURRENT, channels) == (
        grand,
        SignalType.AI_CURRENT,
    )
    assert plc_allocation._serving(model, None, SignalType.RTD, channels) == (
        None,
        SignalType.RTD,
    )


# ---- matching and taking ------------------------------------------------------------------


def test_a_request_takes_only_a_channel_of_its_own_signal() -> None:
    """A DI request skips the AI module, however early it sorts."""
    plant = Plant()
    _module(plant, "a-ai", signal=SignalType.AI_CURRENT, channels=1)
    (di,) = _module(plant, "z-di", channels=1)
    request = _request(plant, "dev", SignalType.DI)
    assert _run(plant)[0] == {request: di}


def test_a_channel_is_never_bound_twice() -> None:
    """Three requests, two channels: two bindings, distinct channels, one finding."""
    plant = Plant()
    _module(plant, "m", channels=2)
    for name in ("a", "b", "c"):
        _request(plant, name)
    bound, findings = _run(plant)
    assert len(bound) == 2
    assert len(set(bound.values())) == 2
    assert len(findings) == 1


def _with_binding(plant: Plant, name: str, request: Id[Function], channel: Id[Function]) -> None:
    plant.add(
        PlcBindingFacet(
            id=make_id(PlcBindingFacet, ("pre", name)),
            key=("pre", name),
            subject=request,
            channel=channel,
        )
    )


def test_an_existing_binding_is_kept_and_its_channel_stays_taken() -> None:
    """The bound request is skipped (nothing written, nothing reported); the next gets channel 2."""
    plant = Plant()
    first, second = _module(plant, "m", channels=2)
    kept = _request(plant, "a-kept")
    new = _request(plant, "b-new")
    _with_binding(plant, "kept", kept, first)
    bound, findings = _run(plant)
    assert bound == {kept: first, new: second}
    assert findings == ()


def test_a_binding_whose_request_is_gone_still_holds_its_channel() -> None:
    """The pass does not clean up; the channel stays taken."""
    plant = Plant()
    first, second = _module(plant, "m", channels=2)
    orphan = plant.function(plant.item("orphan"), "signal")
    _with_binding(plant, "orphan", orphan, first)
    request = _request(plant, "dev")
    assert _run(plant)[0] == {orphan: first, request: second}


def test_a_binding_to_a_channel_of_another_signal_is_left_to_the_validator() -> None:
    """The pass neither fixes nor reports it; `check_plc` does."""
    plant = Plant()
    (channel,) = _module(plant, "m", signal=SignalType.DO, channels=1)
    request = _request(plant, "dev", SignalType.DI)
    _with_binding(plant, "wrong", request, channel)
    model, findings = allocate_plc(plant.model())
    assert findings == ()
    assert _bound(model) == {request: channel}
    assert len(check_plc(model)) == 1


def test_an_uninstalled_modules_channels_are_allocated_like_any_other() -> None:
    """`installed` is connectivity's concern, not this pass's."""
    plant = Plant()
    (channel,) = _module(plant, "m", channels=1, where=Slot(installed=False))
    request = _request(plant, "dev")
    assert _run(plant)[0] == {request: channel}


# ---- the finding --------------------------------------------------------------------------


def test_no_channel_of_that_signal_at_all_is_an_error_naming_function_and_facet() -> None:
    """One code, the first cause."""
    plant = Plant()
    _module(plant, "m", channels=1)
    function = _request(plant, "dev", SignalType.RTD)
    facet = make_id(PlcRequestFacet, ("dev", "signal", "request"))
    bound, (finding,) = _run(plant)
    assert bound == {}
    assert (finding.code, finding.severity) == (PLC_REQUEST_UNSERVABLE, Severity.ERROR)
    assert finding.subjects == tuple(sorted((facet, function)))
    assert "dev/signal" in finding.message
    assert "rtd" in finding.message
    assert "tag_dev" in finding.message
    assert "declares no" in finding.message


def test_every_channel_of_that_signal_taken_is_the_other_message() -> None:
    """Same code, the second cause."""
    plant = Plant()
    _module(plant, "m", channels=1)
    _request(plant, "a")
    _request(plant, "b")
    _, (finding,) = _run(plant)
    assert "taken" in finding.message
    assert "declares no" not in finding.message


def test_findings_are_sorted_and_messages_never_print_an_id() -> None:
    """Sorted by `(code, subjects, message)`; names, not ids."""
    plant = Plant()
    for number in range(12):
        _request(plant, f"dev-{number:02d}", SignalType.RTD)
    findings = _run(plant)[1]
    assert len(findings) == 12
    assert findings == tuple(sorted(findings, key=lambda f: (f.code, f.subjects, f.message)))
    for finding in findings:
        assert not re.search(r"[0-9a-f]{32}", finding.message)


# ---- the written records ------------------------------------------------------------------


def test_a_binding_has_the_key_and_id_derived_from_its_request() -> None:
    """`(*function.key, "plc_binding")`: a function of the subject alone."""
    plant = Plant()
    (channel,) = _module(plant, "m", channels=1)
    request = _request(plant, "dev")
    model, _ = allocate_plc(plant.model())
    (binding,) = facets_of(model, PlcBindingFacet).values()
    key = ("dev", "signal", "plc_binding")
    assert binding == PlcBindingFacet(
        id=make_id(PlcBindingFacet, key), key=key, subject=request, channel=channel
    )


def test_the_result_satisfies_the_plc_validator() -> None:
    """Whatever the pass binds, `check_plc` finds nothing to say."""
    plant = Plant()
    _module(plant, "di", channels=2)
    _module(plant, "ai", signal=SignalType.AI_CURRENT, channels=2)
    for name, signal in (("a", SignalType.DI), ("b", SignalType.AI_CURRENT), ("c", SignalType.DI)):
        _request(plant, name, signal)
    model, findings = allocate_plc(plant.model())
    assert findings == ()
    assert len(_bound(model)) == 3
    assert check_plc(model) == ()


def _with_origins(plant: Plant) -> Model:
    """Every record on a line of its own."""
    draft = Draft()
    for line, record in enumerate(plant.records, start=1):
        draft.add(record, origin=Origin(file="plant.py", line=line, note=str(record.key)))
    return freeze(draft)


def test_a_binding_cites_the_origin_of_the_request_it_serves_and_evolve_runs_once() -> None:
    """One `evolve`, then each binding gets its request's line back."""
    plant = Plant()
    _module(plant, "m", channels=10)
    names = [f"dev-{n:02d}" for n in range(10)]
    for name in names:
        _request(plant, name)
    model = _with_origins(plant)
    calls: list[int] = []
    real = plc_allocation.evolve

    def counting(*args: Any, **kwargs: Any) -> Model:
        calls.append(1)
        return real(*args, **kwargs)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(plc_allocation, "evolve", counting)
        result, findings = allocate_plc(model)
    assert (len(calls), findings) == (1, ())
    for binding in facets_of(result, PlcBindingFacet).values():
        request = make_id(PlcRequestFacet, (binding.key[0], "signal", "request"))
        assert result.origin_of(binding.id) == model.origin_of(request)


# ---- determinism and identity -------------------------------------------------------------


def _busy() -> Plant:
    plant = Plant()
    _module(plant, "m-b", where=Slot("rack-a", 2), channels=3)
    _module(plant, "m-a", where=Slot("rack-a", 1), channels=3)
    _module(plant, "m-c", where=Slot("rack-b", None), channels=2)
    _module(plant, "ai", signal=SignalType.AI_CURRENT, channels=2)
    for number in range(9):
        _request(plant, f"di-{number}", SignalType.DI, priority=1 + number % 3)
    for number in range(3):
        _request(plant, f"ai-{number}", SignalType.AI_CURRENT)
    return plant


def test_the_result_does_not_depend_on_the_order_of_a_models_tables() -> None:
    """Tables backwards, under another digest: the same bindings and findings."""
    model = _busy().model()
    backwards: Model = dataclasses.replace(
        model,
        digest="reversed-tables-test-plc-allocation-model",  # unique: the caches key on digest
        tables=frozendict(
            {
                kind: frozendict(reversed(table.items()))
                for kind, table in reversed(model.tables.items())
            }
        ),
    )
    forward, forward_findings = allocate_plc(model)
    backward, backward_findings = allocate_plc(backwards)
    assert _bound(backward) == _bound(forward)
    assert backward_findings == forward_findings
    assert len(_bound(forward)) == 10
    assert len(forward_findings) == 2


def test_a_second_run_binds_nothing_new_and_repeats_the_findings() -> None:
    """Idempotent: same `Model` object back, the unservable findings again."""
    model, findings = allocate_plc(_busy().model())
    again, again_findings = allocate_plc(model)
    assert again is model
    assert again_findings == findings


def test_a_model_with_nothing_to_bind_comes_back_as_the_same_object() -> None:
    """No `evolve` at all."""
    plant = Plant()
    _module(plant, "m")
    model = plant.model()
    result, findings = allocate_plc(model)
    assert result is model
    assert findings == ()


def test_only_the_bindings_are_added() -> None:
    """Every other table is the model's own object; the digest moves in `facet` alone."""
    plant = _busy()
    model = plant.model()
    result, _ = allocate_plc(model)
    for kind, table in model.tables.items():
        assert result.tables[kind] is table
    assert result.digests["core"] == model.digests["core"]
    assert result.digests["facet"] != model.digests["facet"]
