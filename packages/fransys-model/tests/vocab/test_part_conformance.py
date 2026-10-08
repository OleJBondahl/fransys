"""WP9 tests: the `part_conformance` validator (ROADMAP WP9, design/vocabulary.md 7)."""

import dataclasses
import re
from typing import TYPE_CHECKING, Any

import pytest
from examples import bundle_records, lamp_part_bundle, relay_part_bundle

from fransys_model.kernel import (
    Draft,
    Finding,
    Id,
    Model,
    Origin,
    Record,
    Severity,
    freeze,
    make_id,
)
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import FunctionKind, PortRole
from fransys_model.vocab.instantiate import PartBundle, instantiate
from fransys_model.vocab.tables import functions
from fransys_model.vocab.validators.part_conformance import (
    ITEM_PART_MISMATCH,
    ITEM_WITHOUT_PART,
    check_part_conformance,
)

if TYPE_CHECKING:
    from collections.abc import Callable

_KEY = ("examples", "relay-1")


def _freeze(records: tuple[Record, ...]) -> Model:
    draft = Draft()
    draft.extend(records, origin=Origin(file="test_part_conformance.py", line=1, note="fixture"))
    return freeze(draft)


def _relay(**kwargs: Any) -> tuple[Record, ...]:
    return instantiate(relay_part_bundle(), _KEY, **kwargs)


def _the[R](records: tuple[Record, ...], record_type: type[R], name: str) -> R:
    """The one `record_type` record called `name`."""
    (found,) = [
        r for r in records if isinstance(r, record_type) and getattr(r, "name", None) == name
    ]
    return found


def _without(records: tuple[Record, ...], *dropped: Record) -> tuple[Record, ...]:
    return tuple(r for r in records if r not in dropped)


def _with(records: tuple[Record, ...], old: Record, new: Record) -> tuple[Record, ...]:
    return tuple(new if r is old else r for r in records)


def _mismatches(records: tuple[Record, ...], bundle: PartBundle | None = None) -> list[Finding]:
    bundle = relay_part_bundle() if bundle is None else bundle
    model = _freeze((*bundle_records(bundle), *records))
    return [f for f in check_part_conformance(model) if f.code == ITEM_PART_MISMATCH]


ITEM_ID = make_id(Item, _KEY)


def _subjects(*ids: Id[Any]) -> tuple[Id[Any], ...]:
    """What a `Finding` stores: each id once, in id order."""
    return tuple(sorted(ids))


def test_conforming_item_has_no_finding() -> None:
    """An item instantiated straight from `instantiate` conforms; no `Finding` is raised."""
    bundle = relay_part_bundle()
    records = instantiate(bundle, ("examples", "relay-1"))
    model = _freeze((*bundle_records(bundle), *records))
    findings = check_part_conformance(model)
    assert not [f for f in findings if f.code == ITEM_PART_MISMATCH]


def test_a_conforming_model_has_no_finding_at_all() -> None:
    """Nothing but `ITEM_PART_MISMATCH` and `ITEM_WITHOUT_PART` exists, and neither applies."""
    bundle = relay_part_bundle()
    model = _freeze((*bundle_records(bundle), *_relay(), *instantiate(bundle, ("examples", "r2"))))
    assert check_part_conformance(model) == ()


def test_an_empty_model_has_no_finding() -> None:
    """No items, nothing to check."""
    assert check_part_conformance(_freeze(())) == ()


def test_added_port_yields_item_part_mismatch() -> None:
    """A hand-added `Port` with no matching `PortTemplate` yields `ITEM_PART_MISMATCH`."""
    bundle = relay_part_bundle()
    records = instantiate(bundle, ("examples", "relay-1"))
    (coil,) = [r.id for r in records if isinstance(r, Function) and r.name == "coil"]
    extra_port = Port(
        id=Id(kind="port", value="e" * 32),
        key=("examples", "relay-1", "fn", "coil", "port", "EXTRA"),
        function=coil,
        template=None,
        name="EXTRA",
        role=PortRole.GENERIC,
    )
    model = _freeze((*bundle_records(bundle), *records, extra_port))
    findings = check_part_conformance(model)
    assert any(f.code == ITEM_PART_MISMATCH for f in findings)


def test_deleted_port_yields_item_part_mismatch() -> None:
    """Dropping one of the template's declared ports yields `ITEM_PART_MISMATCH`."""
    bundle = relay_part_bundle()
    records = instantiate(bundle, ("examples", "relay-1"))
    without_one_port = records[:-1]
    model = _freeze((*bundle_records(bundle), *without_one_port))
    findings = check_part_conformance(model)
    assert any(f.code == ITEM_PART_MISMATCH for f in findings)


def test_item_without_part_is_tracked_not_rejected() -> None:
    """An `Item(part=None)` declaring functions/ports directly yields `ITEM_WITHOUT_PART`."""
    item = Item(
        id=Id(kind="item", value="f" * 32),
        key=("examples", "early-design-item"),
        part=None,
        parent=None,
        position=None,
        tag=None,
        description="Invented item declared before a Part exists",
    )
    model = _freeze((item,))
    findings = check_part_conformance(model)
    assert any(f.code == ITEM_WITHOUT_PART for f in findings)


def _partless(key: str, *, parent: Id[Item] | None = None, external: bool = False) -> Item:
    return Item(
        id=make_id(Item, ("examples", key)),
        key=("examples", key),
        part=None,
        parent=parent,
        position=None,
        tag=None,
        description="",
        external=external,
    )


def test_a_part_less_external_item_and_its_children_give_no_item_without_part() -> None:
    """E6: the flag on a strip or a parent silences the item; a plain part-less item fires."""
    strip = _partless("x8", external=True)
    terminal = _partless("x8-1", parent=strip.id)
    plain = _partless("plain")
    findings = check_part_conformance(_freeze((strip, terminal, plain)))
    assert [f.subjects for f in findings if f.code == ITEM_WITHOUT_PART] == [(plain.id,)]


# ---- each discrepancy is one finding, about the right records ---------------------------


def test_a_deleted_port_is_one_finding_about_the_item_the_function_and_the_template() -> None:
    """The subjects are the item, its function and the port template that has no port."""
    bundle = relay_part_bundle()
    records = _relay()
    lost = _the(records, Port, "A2")
    (finding,) = _mismatches(_without(records, lost))
    template = next(t for t in bundle.port_templates if t.name == "A2")
    assert finding.severity is Severity.ERROR
    assert finding.subjects == _subjects(ITEM_ID, _the(records, Function, "coil").id, template.id)
    assert "A2" in finding.message
    assert "coil" in finding.message


def test_a_deleted_function_with_its_ports_is_one_finding_not_one_per_port() -> None:
    """A function that is gone takes its ports with it: the finding is for the function."""
    bundle = relay_part_bundle()
    records = _relay()
    gone = _the(records, Function, "no_1")
    ports = [r for r in records if isinstance(r, Port) and r.function == gone.id]
    assert len(ports) == 2
    (finding,) = _mismatches(_without(records, gone, *ports))
    template = next(t for t in bundle.function_templates if t.name == "no_1")
    assert finding.subjects == _subjects(ITEM_ID, template.id)
    assert "no_1" in finding.message


def test_a_hand_added_port_is_one_finding_about_it() -> None:
    """The extra port is a subject with the item; nothing else is reported."""
    records = _relay()
    coil = _the(records, Function, "coil")
    extra = Port(
        id=Id(kind="port", value="e" * 32),
        key=("hand", "added"),
        function=coil.id,
        template=None,
        name="EXTRA",
        role=PortRole.GENERIC,
    )
    (finding,) = _mismatches((*records, extra))
    assert finding.subjects == _subjects(ITEM_ID, extra.id)
    assert "EXTRA" in finding.message


def test_a_hand_added_function_is_one_finding_and_its_ports_are_not_reported_again() -> None:
    """A function of no template is the one problem; its own ports follow from it."""
    records = _relay()
    extra = Function(
        id=Id(kind="function", value="e" * 32),
        key=("hand", "added"),
        item=ITEM_ID,
        template=None,
        name="extra",
        kind=FunctionKind.GENERIC,
    )
    port = Port(
        id=Id(kind="port", value="d" * 32),
        key=("hand", "port"),
        function=extra.id,
        template=None,
        name="P",
        role=PortRole.GENERIC,
    )
    (finding,) = _mismatches((*records, extra, port))
    assert finding.subjects == _subjects(ITEM_ID, extra.id)
    assert "extra" in finding.message


def test_a_function_of_a_template_of_another_part_is_a_finding() -> None:
    """A template that belongs to another part is not one of this part's."""
    lamp = lamp_part_bundle()
    records = _relay()
    stranger = Function(
        id=Id(kind="function", value="e" * 32),
        key=("hand", "lamp"),
        item=ITEM_ID,
        template=lamp.function_templates[0].id,
        name="lamp",
        kind=FunctionKind.LOAD,
    )
    model = _freeze(
        (*bundle_records(relay_part_bundle()), *bundle_records(lamp), *records, stranger)
    )
    (finding,) = [f for f in check_part_conformance(model) if f.code == ITEM_PART_MISMATCH]
    assert finding.subjects == _subjects(ITEM_ID, stranger.id)


def test_a_port_of_a_template_of_another_function_is_a_finding() -> None:
    """The pin `13` belongs to `no_1`; on the coil it is a hand-added port."""
    bundle = relay_part_bundle()
    records = _relay()
    p13 = next(t for t in bundle.port_templates if t.name == "13")
    misplaced = Port(
        id=Id(kind="port", value="e" * 32),
        key=("hand", "13"),
        function=_the(records, Function, "coil").id,
        template=p13.id,
        name="13",
        role=PortRole.GENERIC,
    )
    (finding,) = _mismatches((*records, misplaced))
    assert finding.subjects == _subjects(ITEM_ID, misplaced.id)


def test_a_second_function_of_one_template_is_one_finding_about_the_later_id() -> None:
    """The instance is the one with the lowest id; a repeat is reported, once."""
    records = _relay()
    coil = _the(records, Function, "coil")
    twin = dataclasses.replace(coil, id=Id(kind="function", value="f" * 32), key=("hand", "twin"))
    (finding,) = _mismatches((*records, twin))
    repeated = max(coil.id, twin.id)
    assert finding.subjects == _subjects(ITEM_ID, repeated)
    assert "coil" in finding.message


def test_the_ports_of_a_repeated_function_are_not_searched() -> None:
    """A repeat is one finding, whatever hangs under it."""
    records = _relay()
    coil = _the(records, Function, "coil")
    twin = dataclasses.replace(coil, id=Id(kind="function", value="f" * 32), key=("hand", "twin"))
    stray = Port(
        id=Id(kind="port", value="d" * 32),
        key=("hand", "stray"),
        function=twin.id,
        template=None,
        name="P",
        role=PortRole.GENERIC,
    )
    (finding,) = _mismatches((*records, twin, stray))
    assert finding.subjects == _subjects(ITEM_ID, twin.id)


def test_a_second_port_of_one_template_is_one_finding_about_the_later_id() -> None:
    """The same rule for ports."""
    records = _relay()
    a1 = _the(records, Port, "A1")
    twin = dataclasses.replace(a1, id=Id(kind="port", value="f" * 32), key=("hand", "twin"))
    (finding,) = _mismatches((*records, twin))
    assert finding.subjects == _subjects(ITEM_ID, max(a1.id, twin.id))


def test_which_repeat_is_the_instance_does_not_depend_on_the_order_of_a_table() -> None:
    """A table in another order (the model's contract is a set) gives the same findings."""
    bundle = relay_part_bundle()
    records = _relay()
    coil = _the(records, Function, "coil")
    twin = dataclasses.replace(coil, id=Id(kind="function", value="0" * 32), key=("hand", "twin"))
    model = _freeze((*bundle_records(bundle), *records, twin))
    backwards = dataclasses.replace(
        model,
        tables=frozendict(
            {kind: frozendict(reversed(table.items())) for kind, table in model.tables.items()}
        ),
    )
    assert list(functions(backwards)) != list(functions(model))
    assert check_part_conformance(backwards) == check_part_conformance(model)


@pytest.mark.parametrize(
    ("changes", "words"),
    [
        ({"name": "renamed"}, ("name",)),
        ({"kind": FunctionKind.GENERIC}, ("kind",)),
        ({"name": "renamed", "kind": FunctionKind.GENERIC}, ("name", "kind")),
    ],
    ids=["name", "kind", "both"],
)
def test_a_drifted_function_is_one_finding_naming_what_differs(
    changes: dict[str, Any], words: tuple[str, ...]
) -> None:
    """Editing a copied fact away from the template is one finding, however many fields."""
    records = _relay()
    coil = _the(records, Function, "coil")
    (finding,) = _mismatches(_with(records, coil, dataclasses.replace(coil, **changes)))
    assert finding.subjects == _subjects(ITEM_ID, coil.id)
    assert finding.message.endswith(" in " + " and ".join(words))


@pytest.mark.parametrize(
    ("changes", "words"),
    [
        ({"name": "renamed"}, ("name",)),
        ({"role": PortRole.PE}, ("role",)),
        ({"name": "renamed", "role": PortRole.PE}, ("name", "role")),
    ],
    ids=["name", "role", "both"],
)
def test_a_drifted_port_is_one_finding_naming_what_differs(
    changes: dict[str, Any], words: tuple[str, ...]
) -> None:
    """The same for a port."""
    records = _relay()
    a1 = _the(records, Port, "A1")
    (finding,) = _mismatches(_with(records, a1, dataclasses.replace(a1, **changes)))
    assert finding.subjects == _subjects(ITEM_ID, a1.id)
    assert finding.message.endswith(" in " + " and ".join(words))


def _marked_bundle() -> PartBundle:
    """The relay part whose `A1` pin prints `"1"` (decision model-0053)."""
    bundle = relay_part_bundle()
    a1 = next(t for t in bundle.port_templates if t.name == "A1")
    marked = tuple(
        dataclasses.replace(t, marking="1") if t is a1 else t for t in bundle.port_templates
    )
    return dataclasses.replace(bundle, port_templates=marked)


def test_a_port_that_prints_what_its_template_prints_is_no_finding() -> None:
    """Positive control: the same non-None marking on both sides conforms."""
    bundle = _marked_bundle()
    records = instantiate(bundle, _KEY)
    assert _the(records, Port, "A1").marking == "1"
    assert _mismatches(records, bundle) == []


@pytest.mark.parametrize("marking", ["X", "", None], ids=["other", "empty", "none"])
def test_a_marking_that_differs_from_the_template_is_one_finding(marking: str | None) -> None:
    """Editing a port's marking away from its template's is one finding naming `marking`."""
    bundle = _marked_bundle()
    records = instantiate(bundle, _KEY)
    a1 = _the(records, Port, "A1")
    (finding,) = _mismatches(_with(records, a1, dataclasses.replace(a1, marking=marking)), bundle)
    assert finding.severity is Severity.ERROR
    assert finding.subjects == _subjects(ITEM_ID, a1.id)
    assert finding.message.endswith(" in marking")


def test_a_marking_on_a_port_whose_template_has_none_is_one_finding() -> None:
    """The other direction: the template prints the port's name (`None`), the port says `"X"`."""
    records = _relay()
    a1 = _the(records, Port, "A1")
    assert a1.marking is None
    (finding,) = _mismatches(_with(records, a1, dataclasses.replace(a1, marking="X")))
    assert finding.subjects == _subjects(ITEM_ID, a1.id)
    assert finding.message.endswith(" in marking")


def test_a_port_differing_in_name_and_marking_names_both_in_one_finding() -> None:
    """The fields come in the order name, role, marking."""
    records = _relay()
    a1 = _the(records, Port, "A1")
    drifted = dataclasses.replace(a1, name="renamed", marking="X")
    (finding,) = _mismatches(_with(records, a1, drifted))
    assert finding.message.endswith(" in name and marking")


def test_a_drift_is_not_also_reported_as_missing() -> None:
    """The renamed function still stands for its template."""
    records = _relay()
    coil = _the(records, Function, "coil")
    findings = _mismatches(_with(records, coil, dataclasses.replace(coil, name="renamed")))
    assert len(findings) == 1


def test_an_item_that_is_not_installed_is_checked_like_any_other() -> None:
    """`installed=False` leaves it in drawings, so its functions still have to match."""
    records = _relay(installed=False)
    lost = _the(records, Port, "A2")
    assert len(_mismatches(_without(records, lost))) == 1


def test_a_part_with_no_templates_accepts_an_item_with_no_functions() -> None:
    """Nothing declared, nothing present: conforming."""
    bundle = relay_part_bundle()
    bare = PartBundle(part=bundle.part, function_templates=(), port_templates=(), internal_links=())
    assert _mismatches(instantiate(bare, _KEY), bare) == []


def test_a_part_with_no_templates_refuses_a_function_on_its_item() -> None:
    """A function of no template on an item of a template-less part is a hand-added function."""
    bundle = relay_part_bundle()
    bare = PartBundle(part=bundle.part, function_templates=(), port_templates=(), internal_links=())
    (item,) = instantiate(bare, _KEY)
    stray = Function(
        id=Id(kind="function", value="e" * 32),
        key=("hand", "added"),
        item=item.id,
        template=None,
        name="x",
        kind=FunctionKind.GENERIC,
    )
    (finding,) = _mismatches((item, stray), bare)
    assert finding.subjects == _subjects(item.id, stray.id)


def test_only_the_item_that_differs_is_reported() -> None:
    """Two relays, one short of a port: the finding is about that one."""
    bundle = relay_part_bundle()
    other = instantiate(bundle, ("examples", "relay-2"))
    records = _relay()
    lost = _the(records, Port, "A1")
    model = _freeze((*bundle_records(bundle), *_without(records, lost), *other))
    (finding,) = [f for f in check_part_conformance(model) if f.code == ITEM_PART_MISMATCH]
    assert ITEM_ID in finding.subjects
    assert not set(finding.subjects) & {r.id for r in other}


def test_two_discrepancies_on_one_item_are_two_findings() -> None:
    """One finding per discrepancy, not one per item."""
    records = _relay()
    findings = _mismatches(_without(records, _the(records, Port, "A1"), _the(records, Port, "13")))
    assert len(findings) == 2


# ---- items without a part ----------------------------------------------------------------


def _bare_item(key: str, parent: Id[Item] | None = None) -> Item:
    return Item(
        id=Id(kind="item", value=key * 32),
        key=("bare", key),
        part=None,
        parent=parent,
        position=None,
        tag=None,
        description="Invented",
    )


def test_an_item_without_a_part_is_one_info_finding_about_it() -> None:
    """Tracked, not rejected: `INFO`, with the item as its subject."""
    item = _bare_item("a")
    (finding,) = check_part_conformance(_freeze((item,)))
    assert (finding.code, finding.severity, finding.subjects) == (
        ITEM_WITHOUT_PART,
        Severity.INFO,
        (item.id,),
    )


def test_a_container_without_a_part_is_reported_like_any_other_item_without_one() -> None:
    """A strip or a harness housing is an item too: the rule has no exception for containers."""
    strip = _bare_item("a")
    terminal = _bare_item("b", parent=strip.id)
    findings = check_part_conformance(_freeze((strip, terminal)))
    assert [f.subjects for f in findings] == sorted([(strip.id,), (terminal.id,)])


def test_an_item_of_a_part_is_not_an_item_without_one() -> None:
    """`ITEM_WITHOUT_PART` is for `part=None` only."""
    findings = check_part_conformance(_freeze((*bundle_records(relay_part_bundle()), *_relay())))
    assert not [f for f in findings if f.code == ITEM_WITHOUT_PART]


def test_an_item_without_a_part_is_not_checked_for_functions() -> None:
    """It declares functions directly, so nothing is missing or extra."""
    item = _bare_item("a")
    function = Function(
        id=Id(kind="function", value="c" * 32),
        key=("bare", "f"),
        item=item.id,
        template=None,
        name="J1",
        kind=FunctionKind.CONNECTOR,
    )
    findings = check_part_conformance(_freeze((item, function)))
    assert [f.code for f in findings] == [ITEM_WITHOUT_PART]


# ---- what every finding looks like -------------------------------------------------------


def _broken_records() -> tuple[Record, ...]:
    """A relay short a port and a function, with a drifted kind and a hand-added port.

    A part-less item is there too, and its id sorts before every other item's, so the order a
    table lists things in is not the order the findings have to come out in.
    """
    bundle = relay_part_bundle()
    records = _relay()
    coil, no_1, co_1 = (_the(records, Function, name) for name in ("coil", "no_1", "co_1"))
    extra = Port(
        id=Id(kind="port", value="e" * 32),
        key=("hand", "added"),
        function=coil.id,
        template=None,
        name="EXTRA",
        role=PortRole.GENERIC,
    )
    drifted = _with(records, co_1, dataclasses.replace(co_1, kind=FunctionKind.GENERIC))
    no_1_ports = [r for r in records if isinstance(r, Port) and r.function == no_1.id]
    kept = _without(drifted, _the(records, Port, "A1"), no_1, *no_1_ports)
    return (*bundle_records(bundle), *kept, extra, _bare_item("0"))


def _broken_model() -> Model:
    return _freeze(_broken_records())


def test_findings_are_sorted_by_code_subjects_and_message() -> None:
    """The validator sorts what it finds: no order of a table leaks out."""
    findings = check_part_conformance(_broken_model())
    assert [f.code for f in findings] == [ITEM_PART_MISMATCH] * 4 + [ITEM_WITHOUT_PART]
    assert findings == tuple(sorted(findings, key=lambda f: (f.code, f.subjects, f.message)))
    assert [f.subjects for f in findings] != [
        f.subjects for f in sorted(findings, key=lambda f: f.message)
    ]


@pytest.mark.parametrize(
    "reorder", [lambda r: r[::-1], lambda r: r[1:] + r[:1]], ids=["reversed", "rotated"]
)
def test_the_findings_do_not_depend_on_the_order_records_were_added(
    reorder: Callable[[tuple], tuple],
) -> None:
    """Build the same model with the records added in another order: equal findings."""
    everything = _broken_records()
    in_order = check_part_conformance(_freeze(everything))
    assert reorder(everything) != everything
    assert check_part_conformance(_freeze(reorder(everything))) == in_order
    assert len(in_order) == 5


def test_a_message_names_things_and_never_prints_an_id() -> None:
    """Ids are opaque: a human reads names, and `describe` turns the subjects into origins."""
    for finding in check_part_conformance(_broken_model()):
        assert not re.search(r"[0-9a-f]{32}", finding.message)
        assert finding.message


def test_the_validator_is_repeatable() -> None:
    """A pure function of the model."""
    model = _broken_model()
    assert check_part_conformance(model) == check_part_conformance(model)
