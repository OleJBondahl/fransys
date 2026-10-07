"""WP6 tests: `kernel.encode`, the model as nested data and as canonical JSON
(design/kernel-model.md 5.6).

Every expected value below is written out by hand, never computed by the code under test.
"""

import json
from decimal import Decimal
from typing import Any

import pytest
from canon_probes import (
    CanonDetail,
    Shade,
    make_item,
    make_owner,
    model_of,
    owner_id,
)

from fransys_model.kernel import Origin, ValueTypeError
from fransys_model.kernel.encode import (
    JsonValue,
    decimal_text,
    record_data,
    to_data,
    write_json,
)


def _write(data: JsonValue, *, compact: bool = False) -> str:
    """`write_json` for the kernel's own frozen data (`frozendict`, tuples), which it writes too."""
    return write_json(data, compact=compact)


@pytest.mark.parametrize(
    ("given", "written"),
    [
        ("1.50", "1.5"),
        ("1.5", "1.5"),
        ("0.00", "0"),
        ("-0", "0"),
        ("0E-7", "0"),
        ("-0.000", "0"),
        ("-1.230", "-1.23"),
        ("10", "10"),
        ("1E+2", "100"),
        ("1E+30", "1" + "0" * 30),
        ("123.456", "123.456"),
        ("0.750", "0.75"),
        ("1." + "2" * 40, "1." + "2" * 40),
    ],
)
def test_a_decimal_has_one_canonical_string(given: str, written: str) -> None:
    """Equal `Decimal`s write alike, and no digit is lost to a context precision."""
    assert decimal_text(Decimal(given)) == written
    assert Decimal(written) == Decimal(given)


def test_two_spellings_of_one_decimal_write_the_same_bytes() -> None:
    """`Decimal("1.50")` and `Decimal("1.5")` compare and hash equal, and must dump equal."""
    assert Decimal("1.50") == Decimal("1.5")
    assert decimal_text(Decimal("1.50")) == decimal_text(Decimal("1.5"))


def test_a_record_is_written_field_by_field_with_every_field_present() -> None:
    """Ids as `kind:hex`, a `Decimal` as its canonical string, an enum by its value."""
    item = make_item("2", maybe=owner_id("1"), note=None)
    expected = {
        "amount": "1.5",
        "count": 3,
        "details": [],
        "ext": {},
        "flag": True,
        "id": "canon_item_probe:" + "2" * 32,
        "key": ["2"],
        "level": 2,
        "maybe": "canon_owner_probe:" + "1" * 32,
        "name": "pump",
        "note": None,
        "owner": "canon_owner_probe:" + "1" * 32,
        "scores": {"x": 1},
        "shade": "red",
        "tags": ["a", "b"],
    }
    assert json.loads(_write(record_data(item), compact=True)) == expected


def test_a_multi_segment_key_is_written_as_a_json_array_of_strings() -> None:
    """`AuthoringKey` is `tuple[str, ...]`: every segment is encoded, not dropped or mis-typed.

    If `_encode_value` forgot to unwrap the alias (`annotation.__value__`), the key would
    still reach `json.dumps` as a tuple of strings and look right by accident for a
    single-segment key; a multi-segment key makes the per-item walk observable.
    """
    item = make_item("2", key=("a", "b", "c"))
    written = json.loads(_write(record_data(item), compact=True))["key"]
    assert written == ["a", "b", "c"]
    assert all(isinstance(segment, str) for segment in written)


def test_a_nested_value_is_written_as_a_mapping_of_its_fields() -> None:
    """A `@value` inside a tuple has no tag of its own: its annotation says what it is."""
    detail = CanonDetail(amount=Decimal("2.50"), owner=owner_id("1"), shade=Shade.BLUE)
    data = record_data(make_item("2", details=(detail,)))
    assert json.loads(_write(data, compact=True))["details"] == [
        {"amount": "2.5", "owner": "canon_owner_probe:" + "1" * 32, "shade": "blue"}
    ]


def test_an_undeclared_position_tags_what_json_cannot_tell_apart() -> None:
    """Under `ext` a mapping is `$map` and an id `$id`; scalars and tuples stand for themselves."""
    ext = frozendict(
        {
            "map": frozendict({"a.b": 1}),
            "id": owner_id("1"),
            "tuple": ("x", 2, None, True),
            "text": "1.5",
        }
    )
    written = json.loads(_write(record_data(make_item("2", ext=ext)), compact=True))["ext"]
    assert written == {
        "id": {"$id": "canon_owner_probe:" + "1" * 32},
        "map": {"$map": {"a.b": 1}},
        "text": "1.5",
        "tuple": ["x", 2, None, True],
    }


def test_a_key_that_looks_like_a_tag_cannot_be_mistaken_for_one() -> None:
    """Tags are read only inside a value: a mapping there is always `$map`, so `$id` is a key.

    `ext` itself is a declared mapping, so its own keys are plain, tag-shaped or not.
    """
    ext = frozendict({"$id": "at the ext level", "k": frozendict({"$id": "inside a value"})})
    written = json.loads(_write(record_data(make_item("2", ext=ext)), compact=True))["ext"]
    assert written == {"$id": "at the ext level", "k": {"$map": {"$id": "inside a value"}}}


def test_the_model_is_tables_of_records_in_id_order_plus_aliases(origin: Origin) -> None:
    """`to_data` carries the schema version, aliases and tables, and nothing derived."""
    second, first = make_item("3"), make_item("2")
    model = model_of(origin, second, first, make_owner("1"))
    data = to_data(model)
    assert list(data) == ["aliases", "schema_version", "tables"]
    assert data["schema_version"] == 9
    assert data["aliases"] == ()
    assert list(data["tables"]) == ["canon_item_probe", "canon_owner_probe"]
    assert [entry["key"] for entry in data["tables"]["canon_item_probe"]] == [("2",), ("3",)]


def test_aliases_are_written_as_sorted_pairs_of_ids(origin: Origin) -> None:
    """Retired id first, current id second, in retired-id order."""
    from canon_probes import draft_of

    from fransys_model.kernel import freeze

    draft = draft_of(origin, make_owner("1"))
    draft.alias(owner_id("9"), owner_id("1"))
    draft.alias(owner_id("7"), owner_id("1"))
    written = to_data(freeze(draft))["aliases"]
    assert written == (
        ("canon_owner_probe:" + "7" * 32, "canon_owner_probe:" + "1" * 32),
        ("canon_owner_probe:" + "9" * 32, "canon_owner_probe:" + "1" * 32),
    )


def test_neither_origins_nor_hashes_are_written(origin: Origin) -> None:
    """Origins are not part of the plant, and hashes and digests are derived (invariant 8)."""
    text = _write(to_data(model_of(origin, make_owner("1"))))
    assert "conftest.py" not in text
    assert "digest" not in text
    assert "hashes" not in text


def test_the_readable_form_is_indented_sorted_utf8_and_ends_in_a_newline() -> None:
    """Golden files diff line by line and keep Norwegian text readable."""
    text = _write(frozendict({"b": "Ærlig vær å", "a": (1, 2)}))
    assert text == '{\n  "a": [\n    1,\n    2\n  ],\n  "b": "Ærlig vær å"\n}\n'


def test_the_compact_form_is_what_gets_hashed() -> None:
    """No spaces, no newline, keys sorted, non-ASCII kept."""
    assert _write(frozendict({"b": "å", "a": (1, 2)}), compact=True) == '{"a":[1,2],"b":"å"}'


def test_the_writer_refuses_a_type_it_cannot_write() -> None:
    """A stray object is a `ValueTypeError`, never a stdlib `TypeError`."""
    stray: Any = frozendict({"a": object()})
    with pytest.raises(ValueTypeError):
        _write(stray)


def test_an_id_is_written_as_its_kind_and_value() -> None:
    """The item's own id is written as `kind:value` text."""
    assert record_data(make_item("2"))["id"] == "canon_item_probe:" + "2" * 32


def test_encoding_does_not_depend_on_field_order_in_a_mapping() -> None:
    """Two equal mappings built in different orders write the same bytes."""
    one: Any = frozendict({"a": 1, "b": 2})
    two: Any = frozendict({"b": 2, "a": 1})
    assert one == two
    assert _write(one) == _write(two)


def test_mapping_keys_are_sorted_in_the_data_and_not_only_in_the_text() -> None:
    """A caller of `to_data` sees the order `dumps` writes, declared position or not."""
    ext = frozendict({"z": 1, "a": frozendict({"zz": 1, "aa": 2})})
    written = record_data(make_item("2", ext=ext, scores=frozendict({"y": 1, "b": 2})))
    assert list(written["ext"]) == ["a", "z"]
    assert list(written["ext"]["a"]["$map"]) == ["aa", "zz"]
    assert list(written["scores"]) == ["b", "y"]
