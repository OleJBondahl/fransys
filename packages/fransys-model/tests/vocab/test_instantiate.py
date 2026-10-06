"""WP9 tests: `vocab.instantiate` and `PartBundle` (ROADMAP WP9, design/kernel-records.md 5.2,
design/vocabulary.md 7, design/examples.md 11)."""

import dataclasses
from typing import TYPE_CHECKING, Any, cast

import pytest
from examples import bundle_records, lamp_part_bundle, relay_part_bundle

from fransys_model.kernel import Draft, Origin, SchemaError, freeze, make_id
from fransys_model.vocab.core import Function, Item, Port
from fransys_model.vocab.enums import PortRole
from fransys_model.vocab.instantiate import PartBundle, instantiate
from fransys_model.vocab.templates import FunctionTemplate, InternalLink, PortTemplate

if TYPE_CHECKING:
    from collections.abc import Callable

_KEY = ("examples", "relay-1")


def _reversed(templates: tuple) -> tuple:
    return templates[::-1]


def _rotated(templates: tuple) -> tuple:
    return templates[1:] + templates[:1]


def _stamped(bundle: PartBundle | None = None, key: tuple[str, ...] = _KEY, **kwargs: Any) -> tuple:
    return instantiate(relay_part_bundle() if bundle is None else bundle, key, **kwargs)


def _only[R](records: tuple, record_type: type[R]) -> list[R]:
    return [r for r in records if isinstance(r, record_type)]


def test_instantiate_relay_yields_one_item_three_functions_seven_ports() -> None:
    """The examples.md relay example instantiates to 1 item, 3 functions, 7 ports."""
    bundle = relay_part_bundle()
    records = instantiate(bundle, ("examples", "relay-1"))
    items = [r for r in records if isinstance(r, Item)]
    functions = [r for r in records if isinstance(r, Function)]
    ports = [r for r in records if isinstance(r, Port)]
    assert len(items) == 1
    assert len(functions) == 3
    assert len(ports) == 7


def test_instantiate_is_deterministic_across_calls() -> None:
    """Calling `instantiate` twice with the same key produces the same ids (kernel-records.md)."""
    bundle = relay_part_bundle()
    first = instantiate(bundle, ("examples", "relay-1"))
    second = instantiate(bundle, ("examples", "relay-1"))
    assert {r.id for r in first} == {r.id for r in second}


def test_instantiate_respects_designation_parent_and_installed() -> None:
    """`tag`, `parent` and `installed` land on the stamped `Item` (design/vocabulary.md 6)."""
    bundle = relay_part_bundle()
    records = instantiate(
        bundle,
        ("examples", "relay-1"),
        tag="-K1",
        description="Invented example relay instance",
        installed=False,
    )
    (item,) = [r for r in records if isinstance(r, Item)]
    assert item.tag == "-K1"
    assert item.installed is False


def test_the_item_carries_the_part_the_key_and_every_argument() -> None:
    """Nothing the caller passed is dropped or defaulted over."""
    parent = make_id(Item, ("examples", "cabinet"))
    (item,) = _only(
        _stamped(tag="-K1", parent=parent, position=4, description="d", installed=False),
        Item,
    )
    assert item == Item(
        id=make_id(Item, _KEY),
        key=_KEY,
        part=relay_part_bundle().part.id,
        parent=parent,
        position=4,
        tag="-K1",
        description="d",
        installed=False,
    )


def test_the_arguments_default_to_an_installed_item_with_nothing_else() -> None:
    """`installed` is true, `tag`/`parent`/`position` are absent, the description empty."""
    (item,) = _only(_stamped(), Item)
    assert (item.tag, item.parent, item.position, item.description, item.installed) == (
        None,
        None,
        None,
        "",
        True,
    )


def test_every_function_copies_its_template_and_takes_a_key_from_the_names() -> None:
    """A function's key is the item key, `fn`, the template's name; `name` and `kind` are copied."""
    bundle = relay_part_bundle()
    functions = _only(_stamped(bundle), Function)
    assert {f.name for f in functions} == {"coil", "no_1", "co_1"}
    templates = {t.id: t for t in bundle.function_templates}
    for function in functions:
        assert function.template is not None
        template = templates[function.template]
        assert function.key == (*_KEY, "fn", template.name)
        assert function.id == make_id(Function, function.key)
        assert function.item == make_id(Item, _KEY)
        assert (function.name, function.kind) == (template.name, template.kind)
    assert {f.template for f in functions} == set(templates)


def test_every_port_copies_its_template_and_hangs_under_its_own_function() -> None:
    """A port's key is its function's key, `port` and the name; `name` and `role` are copied."""
    bundle = relay_part_bundle()
    records = _stamped(bundle)
    function_of = {f.template: f for f in _only(records, Function)}
    templates = {t.id: t for t in bundle.port_templates}
    ports = _only(records, Port)
    assert {p.template for p in ports} == set(templates)
    for port in ports:
        assert port.template is not None
        template = templates[port.template]
        function = function_of[template.function]
        assert port.function == function.id
        assert port.key == (*function.key, "port", template.name)
        assert port.id == make_id(Port, port.key)
        assert (port.name, port.role) == (template.name, template.role)


def test_a_port_name_used_by_two_functions_is_two_ports() -> None:
    """The relay has pin `14` on both contacts: each function gets its own port, ids apart."""
    ports = [p for p in _only(_stamped(), Port) if p.name == "14"]
    assert len(ports) == 2
    assert ports[0].id != ports[1].id
    assert ports[0].function != ports[1].function


def test_a_port_role_other_than_generic_is_copied() -> None:
    """`role` comes from the template, not a default."""
    bundle = lamp_part_bundle()
    (x1, x2) = bundle.port_templates
    changed = dataclasses.replace(
        bundle, port_templates=(dataclasses.replace(x1, role=PortRole.PE), x2)
    )
    roles = {p.name: p.role for p in _only(_stamped(changed), Port)}
    assert roles == {"X1": PortRole.PE, "X2": PortRole.GENERIC}


def test_a_port_marking_is_copied() -> None:
    """model-0053 (F2): `marking` comes from the template, not a default; `None` is copied too."""
    bundle = lamp_part_bundle()
    (x1, x2) = bundle.port_templates
    changed = dataclasses.replace(
        bundle, port_templates=(dataclasses.replace(x1, marking="X9"), x2)
    )
    markings = {p.name: p.marking for p in _only(_stamped(changed), Port)}
    assert markings == {"X1": "X9", "X2": None}


def test_nothing_is_stamped_for_an_internal_link() -> None:
    """Links live on the part; an instance reaches them via its port templates (connectivity.md)."""
    records = _stamped()
    assert {type(r) for r in records} == {Item, Function, Port}
    assert not _only(records, InternalLink)


def test_records_come_back_in_id_order_so_a_port_is_last() -> None:
    """The order is a sort by `id`, never the order the templates were listed in."""
    records = _stamped()
    assert list(records) == sorted(records, key=lambda r: r.id)
    assert isinstance(records[-1], Port)
    assert isinstance(records[0], Function)


@pytest.mark.parametrize("reorder", [_reversed, _rotated], ids=["reversed", "rotated"])
def test_the_order_the_bundle_lists_its_templates_in_changes_nothing(
    reorder: Callable[[tuple], tuple],
) -> None:
    """Listing the templates in another order gives equal records, in the same order."""
    bundle = relay_part_bundle()
    reordered = dataclasses.replace(
        bundle,
        function_templates=reorder(bundle.function_templates),
        port_templates=reorder(bundle.port_templates),
    )
    assert reordered.function_templates != bundle.function_templates
    assert reordered.port_templates != bundle.port_templates
    assert _stamped(reordered) == _stamped(bundle)


def _new_key(old: tuple[str, ...]) -> tuple[str, ...]:
    return ("elsewhere", *old)


def test_ids_come_from_names_not_from_template_ids() -> None:
    """Re-keying every template (new ids, same names) keeps stamped ids (kernel-records.md)."""
    bundle = relay_part_bundle()
    functions = tuple(
        dataclasses.replace(t, key=_new_key(t.key), id=make_id(FunctionTemplate, _new_key(t.key)))
        for t in bundle.function_templates
    )
    by_old = {old.id: new.id for old, new in zip(bundle.function_templates, functions, strict=True)}
    ports = tuple(
        dataclasses.replace(
            t,
            function=by_old[t.function],
            key=_new_key(t.key),
            id=make_id(PortTemplate, _new_key(t.key)),
        )
        for t in bundle.port_templates
    )
    rekeyed = dataclasses.replace(
        bundle, function_templates=functions, port_templates=ports, internal_links=()
    )
    assert {r.id for r in _stamped(rekeyed)} == {r.id for r in _stamped(bundle)}


def test_another_item_key_gives_another_set_of_ids_and_both_fit_in_one_model() -> None:
    """Two relays of one part share nothing but the part: nothing collides at freeze."""
    bundle = relay_part_bundle()
    first, second = _stamped(bundle, ("plant", "k1")), _stamped(bundle, ("plant", "k2"))
    assert not {r.id for r in first} & {r.id for r in second}
    draft = Draft()
    draft.extend(
        (*bundle_records(bundle), *first, *second), origin=Origin(file="t.py", line=1, note="x")
    )
    assert len(freeze(draft).tables["function"]) == 6


def test_the_stamped_records_freeze_with_the_bundle() -> None:
    """Every template and part reference resolves, and the kinds line up (freeze checks both)."""
    bundle = relay_part_bundle()
    draft = Draft()
    draft.extend(
        (*bundle_records(bundle), *_stamped(bundle)), origin=Origin(file="t.py", line=1, note="x")
    )
    model = freeze(draft)
    assert len(model.tables["port"]) == 7


def test_a_part_with_no_templates_stamps_the_item_alone() -> None:
    """Nothing to copy is not an error: the item is the whole result."""
    bundle = relay_part_bundle()
    bare = PartBundle(part=bundle.part, function_templates=(), port_templates=(), internal_links=())
    (item,) = _stamped(bare)
    assert isinstance(item, Item)


def test_a_function_template_with_no_ports_stamps_a_function_with_none() -> None:
    """A port-less function (a bare marker) is stamped, with no port under it."""
    lamp = lamp_part_bundle()
    bare = dataclasses.replace(lamp, port_templates=())
    records = _stamped(bare)
    assert [type(r) for r in records] == [Function, Item]


@pytest.mark.parametrize("bad_key", [(), ("",), ("a", ""), ("a\x1fb",)])
def test_a_bad_item_key_is_refused_by_make_id(bad_key: tuple[str, ...]) -> None:
    """The item key is validated once, where the id is derived (design/kernel-records.md 5.2)."""
    with pytest.raises(SchemaError):
        _stamped(key=bad_key)


def test_a_template_name_that_cannot_be_a_key_segment_is_refused() -> None:
    """An empty function name has no key of its own: `SchemaError`, not a silent collision."""
    lamp = lamp_part_bundle()
    nameless = dataclasses.replace(lamp.function_templates[0], name="")
    bad = dataclasses.replace(lamp, function_templates=(nameless,), port_templates=())
    with pytest.raises(SchemaError):
        _stamped(bad)


def test_a_bundle_is_a_frozen_keyword_only_record_of_tuples() -> None:
    """Plain frozen dataclass (decision 0012): no assignment, no positional construction."""
    bundle = relay_part_bundle()
    with pytest.raises(dataclasses.FrozenInstanceError):
        cast("Any", bundle).part = lamp_part_bundle().part
    positional: Any = PartBundle
    with pytest.raises(TypeError):
        positional(bundle.part, (), (), ())


# ---- PartBundle refuses what could not be one part's templates --------------------------


def _relay_with(**changes: Any) -> PartBundle:
    return dataclasses.replace(relay_part_bundle(), **changes)


def _rekeyed(template: Any, *segment: str) -> Any:
    """A copy of `template` under another key, so another id."""
    key = (*template.key, *segment)
    return dataclasses.replace(template, key=key, id=make_id(type(template), key))


def test_a_function_template_of_another_part_is_refused() -> None:
    """Every template of a bundle belongs to the bundle's own part."""
    bundle = relay_part_bundle()
    stranger = dataclasses.replace(bundle.function_templates[0], part=lamp_part_bundle().part.id)
    with pytest.raises(SchemaError, match="another part") as excinfo:
        _relay_with(function_templates=(stranger, *bundle.function_templates[1:]))
    assert excinfo.value.record_id == stranger.id


def test_a_port_template_of_a_function_template_outside_the_bundle_is_refused() -> None:
    """A pin whose function is not in the bundle would never be stamped."""
    bundle = relay_part_bundle()
    stray = dataclasses.replace(
        bundle.port_templates[0], function=lamp_part_bundle().function_templates[0].id
    )
    with pytest.raises(SchemaError, match="function template") as excinfo:
        _relay_with(port_templates=(stray, *bundle.port_templates[1:]))
    assert excinfo.value.record_id == stray.id


@pytest.mark.parametrize("end", ["a", "b"])
def test_an_internal_link_with_an_end_outside_the_bundle_is_refused(end: str) -> None:
    """Both ends of a link must be port templates of this bundle."""
    bundle = relay_part_bundle()
    outside = lamp_part_bundle().port_templates[0].id
    link = dataclasses.replace(bundle.internal_links[0], **{end: outside})
    with pytest.raises(SchemaError, match="internal link") as excinfo:
        _relay_with(internal_links=(link, *bundle.internal_links[1:]))
    assert excinfo.value.record_id == link.id


_REGISTERED_KIND = {
    "function_templates": "function_template",
    "port_templates": "port_template",
    "internal_links": "internal_link",
}


@pytest.mark.parametrize("field", list(_REGISTERED_KIND))
def test_a_template_listed_twice_is_refused(field: str) -> None:
    """The same id twice would stamp two records under one key; the error names its kind."""
    bundle = relay_part_bundle()
    listed: tuple = getattr(bundle, field)
    with pytest.raises(SchemaError, match="twice") as excinfo:
        _relay_with(**{field: (*listed, listed[0])})
    assert excinfo.value.record_id == listed[0].id
    assert excinfo.value.kind == _REGISTERED_KIND[field]


def test_two_function_templates_with_one_name_are_refused() -> None:
    """Names make the keys, so two of one name would collide in the instance."""
    bundle = relay_part_bundle()
    twin = _rekeyed(bundle.function_templates[0], "twin")
    with pytest.raises(SchemaError, match="name") as excinfo:
        _relay_with(function_templates=(*bundle.function_templates, twin))
    assert excinfo.value.record_id == max(twin.id, bundle.function_templates[0].id)


def test_two_port_templates_of_one_function_with_one_name_are_refused() -> None:
    """Within one function template a port name is unique; across templates it may repeat."""
    bundle = relay_part_bundle()
    twin = _rekeyed(bundle.port_templates[0], "twin")
    with pytest.raises(SchemaError, match="name") as excinfo:
        _relay_with(port_templates=(*bundle.port_templates, twin))
    assert excinfo.value.kind == "port_template"


def test_two_port_templates_of_different_functions_with_one_name_are_allowed() -> None:
    """A port name may repeat across function templates; only a shared function refuses it."""
    bundle = relay_part_bundle()
    coil_a1 = bundle.port_templates[0]
    no_1_p13 = bundle.port_templates[2]
    assert coil_a1.function != no_1_p13.function
    renamed = dataclasses.replace(coil_a1, name=no_1_p13.name)
    changed = _relay_with(port_templates=(renamed, *bundle.port_templates[1:]))
    assert changed.port_templates[0].name == no_1_p13.name


def test_two_internal_links_between_the_same_ports_but_different_ids_are_allowed() -> None:
    """Internal links are deduplicated by id, not by their a/b/kind values."""
    bundle = relay_part_bundle()
    original = bundle.internal_links[0]
    duplicate_value = _rekeyed(original, "again")
    changed = _relay_with(internal_links=(*bundle.internal_links, duplicate_value))
    assert len(changed.internal_links) == len(bundle.internal_links) + 1
    assert duplicate_value.id != original.id
    assert (duplicate_value.a, duplicate_value.b) == (original.a, original.b)


@pytest.mark.parametrize("reorder", [_reversed, _rotated], ids=["reversed", "rotated"])
@pytest.mark.parametrize("field", ["function_templates", "port_templates"])
def test_the_template_a_refusal_names_does_not_depend_on_the_listing_order(
    field: str, reorder: Callable[[tuple], tuple]
) -> None:
    """A name clash is reported against the same record however the templates are listed."""
    bundle = relay_part_bundle()
    listed: tuple = getattr(bundle, field)
    listing = (*listed, _rekeyed(listed[0], "twin"))
    named = set()
    for order in (listing, reorder(listing)):
        with pytest.raises(SchemaError) as excinfo:
            _relay_with(**{field: order})
        named.add(excinfo.value.record_id)
    assert len(named) == 1


def _strangers() -> dict[str, tuple[str, tuple]]:
    """For each refusal that names an offender: the field and a listing with two offenders."""
    bundle = relay_part_bundle()
    lamp = lamp_part_bundle()
    functions = tuple(
        dataclasses.replace(t, part=lamp.part.id) for t in bundle.function_templates[:2]
    )
    outside = lamp.function_templates[0].id
    ports = tuple(dataclasses.replace(t, function=outside) for t in bundle.port_templates[:2])
    lost = lamp.port_templates[0].id
    links = tuple(dataclasses.replace(link, a=lost) for link in bundle.internal_links)
    return {
        "function_template": ("function_templates", functions + bundle.function_templates[2:]),
        "port_template": ("port_templates", ports + bundle.port_templates[2:]),
        "internal_link": ("internal_links", links),
    }


@pytest.mark.parametrize("reorder", [_reversed, _rotated], ids=["reversed", "rotated"])
@pytest.mark.parametrize("kind", ["function_template", "port_template", "internal_link"])
def test_a_refusal_with_two_offenders_names_the_lowest_id_whatever_the_listing_order(
    kind: str, reorder: Callable[[tuple], tuple]
) -> None:
    """Every refusal that names a record checks in id order, so listing order never shows."""
    field, listing = _strangers()[kind]
    offenders = [t for t in listing if t not in getattr(relay_part_bundle(), field)]
    assert len(offenders) == 2
    assert reorder(listing) != listing
    for order in (listing, reorder(listing)):
        with pytest.raises(SchemaError) as excinfo:
            _relay_with(**{field: order})
        assert excinfo.value.record_id == min(t.id for t in offenders)
        assert excinfo.value.kind == kind
