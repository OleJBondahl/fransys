"""Every settings accessor has a production caller, or sits in the shrinking list (R503 W1).

The house text records are read only through the accessors of `derive.facts.house_settings`. An
accessor nobody calls is a record nothing reads, so its settings table has no effect. The list
of such accessors only shrinks and is empty at the 0.22 tag.
"""

import ast
from typing import Any, cast
lazy from collections.abc import Mapping

from gate_scan import src_modules

HOMES = ("fransys_model.derive.facts.house_settings", "fransys_model.derive.house_settings")
# Rises are refused; a name leaves when a reader calls it. Empty at the 0.22 tag.
UNREAD: frozenset[str] = frozenset({"colour_codes_of"})


def accessors() -> frozenset[str]:
    """The public `*_of` accessors the one reader module exports."""
    from fransys_model.derive.facts import house_settings

    return frozenset(n for n in house_settings.__all__ if n.endswith("_of"))


def called_names(sources: Mapping[str, str]) -> frozenset[str]:
    """The names called in the modules that are not an accessor's home."""
    found: set[str] = set()
    for module, source in sources.items():
        if module in HOMES:
            continue
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Call):
                func = node.func
                found.add(func.id if isinstance(func, ast.Name) else getattr(func, "attr", ""))
    return frozenset(found)


def unread(sources: Mapping[str, str]) -> frozenset[str]:
    """The accessors no module outside their home calls."""
    return accessors() - called_names(sources)


def test_the_accessors_with_no_production_caller_are_the_listed_ones():
    sources = {m: p.read_text(encoding="utf-8") for m, p in src_modules()}
    assert unread(sources) == UNREAD


def test_the_gate_can_fail():
    names = sorted(accessors())
    caller = "\n".join(f"{n}(model)" for n in names[1:])
    assert unread({"fransys_pdf.x": caller}) == {names[0]}
    only_home = {HOMES[0]: "\n".join(f"{n}(model)" for n in names)}
    assert unread(only_home) == accessors()


FIELD_HOMES = ("fransys_model.layout.house_text", "fransys_model.layout.house_builders")
# Fields the accessors' readers leave alone: a record's identity and its extension slot.
NOT_SETTINGS = frozenset({"id", "key", "ext"})
# Rises are refused; a field leaves when a reader reads it. Empty at the 0.22 tag.
UNREAD_FIELDS: frozenset[str] = frozenset(
    {
        "ColourCodes.defaults",
        "ColourCodes.shield",
    }
)


def record_fields() -> frozenset[str]:
    """Every settings field of every house text record, as `Record.field`."""
    import dataclasses

    from fransys_model.layout import HOUSE_TEXT_KINDS

    return frozenset(
        f"{cls.__name__}.{f.name}"
        for cls in HOUSE_TEXT_KINDS
        for f in dataclasses.fields(cast("Any", cls))
        if f.name not in NOT_SETTINGS
    )


def read_attrs(sources: Mapping[str, str]) -> frozenset[str]:
    """The attribute names read in the modules that are not a record's definition or builder."""
    found: set[str] = set()
    for module, source in sources.items():
        if module in FIELD_HOMES:
            continue
        found.update(n.attr for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Attribute))
    return frozenset(found)


def unread_fields(sources: Mapping[str, str]) -> frozenset[str]:
    """The record fields whose name no module outside their definition reads as an attribute."""
    attrs = read_attrs(sources)
    return frozenset(f for f in record_fields() if f.split(".")[1] not in attrs)


def test_the_house_record_fields_with_no_reader_are_the_listed_ones():
    sources = {m: p.read_text(encoding="utf-8") for m, p in src_modules()}
    assert unread_fields(sources) == UNREAD_FIELDS


def test_the_field_gate_can_fail():
    fields = sorted(record_fields())
    reads = "\n".join(f"x.{f.split('.')[1]}" for f in fields[1:])
    assert unread_fields({"fransys_pdf.x": reads}) == {fields[0]}
    assert unread_fields({FIELD_HOMES[0]: "\n".join(f"x.{f.split('.')[1]}" for f in fields)}) == (
        frozenset(fields)
    )
