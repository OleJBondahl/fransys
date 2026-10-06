"""WP6 tests: `from_data` and `loads` on input that is not what `dumps` wrote
(design/kernel-model.md 5.6).

Each case takes a real `dumps` output, corrupts one thing with plain `json`, and reads it
back, so the corruption does not depend on the decoder under test.
"""

import json
from copy import deepcopy
from decimal import Decimal
from typing import Any

import pytest
from canon_probes import (
    CanonDerived,
    derived_id,
    item_id,
    make_item,
    make_owner,
    model_of,
    owner_id,
)
from freeze_probes import Pair, draft_of
from freeze_probes import make_owner as make_freeze_owner

from fransys_model.kernel import (
    SCHEMA_VERSION,
    FreezeError,
    Id,
    MergeConflict,
    Origin,
    RefError,
    SchemaError,
    SchemaVersionError,
    ValueTypeError,
    dumps,
    freeze,
    from_data,
    loads,
)
from fransys_model.kernel.decode import MAX_EXPONENT, _decimal, _decode_plain, _decode_value
from fransys_model.kernel.encode import to_data
from fransys_model.kernel.schema import key_and_value_aliases

_ORIGIN = Origin(file="decode.py", line=1, note="")


def _base() -> dict[str, Any]:
    """Plain-`json` form of a small valid model: two owners and an item."""
    model = model_of(_ORIGIN, make_owner("1"), make_owner("4"), make_item("2"))
    return json.loads(dumps(model))


def _read(data: Any) -> Any:
    return loads(json.dumps(data))


def _item(data: dict[str, Any]) -> dict[str, Any]:
    return data["tables"]["canon_item_probe"][0]


def _errors_of(data: Any) -> tuple[Any, ...]:
    with pytest.raises(FreezeError) as excinfo:
        _read(data)
    return excinfo.value.errors


def test_the_untouched_base_loads() -> None:
    """The corruptions below start from something that reads back fine."""
    assert _read(_base()).tables["canon_item_probe"][item_id("2")].name == "pump"


@pytest.mark.parametrize("text", ["[]", "3", '"x"', "null"], ids=["array", "int", "str", "null"])
def test_the_top_level_must_be_a_mapping(text: str) -> None:
    """Anything else has no record to attach a problem to, so it raises directly."""
    with pytest.raises(SchemaError, match="not a mapping") as excinfo:
        loads(text)
    assert excinfo.value.kind == "canonical"


@pytest.mark.parametrize("version", ["1", True, None, [1]], ids=["str", "bool", "none", "array"])
def test_a_schema_version_that_is_not_an_int_is_a_schema_error(version: Any) -> None:
    """`True` is not a version, and neither is `"1"`; a float never gets this far (see below)."""
    data = _base()
    data["schema_version"] = version
    with pytest.raises(SchemaError, match="schema_version"):
        _read(data)


def test_a_missing_schema_version_is_a_schema_error() -> None:
    """The version is the first thing looked for."""
    data = _base()
    del data["schema_version"]
    with pytest.raises(SchemaError, match="schema_version") as excinfo:
        _read(data)
    assert excinfo.value.kind == "canonical"


def test_a_schema_version_this_build_does_not_know_is_a_version_error() -> None:
    """A different int is a hard error carrying both numbers; there is no migration."""
    data = _base()
    data["schema_version"] = SCHEMA_VERSION + 1
    with pytest.raises(SchemaVersionError) as excinfo:
        _read(data)
    assert (excinfo.value.expected, excinfo.value.actual) == (SCHEMA_VERSION, SCHEMA_VERSION + 1)


def test_a_stored_version_1_document_is_refused_naming_both_versions() -> None:
    """SC9: a document of an older schema version is not read, and the message says why.

    Fails if the version check in `from_data` goes, or if `SCHEMA_VERSION` returns to 1.
    """
    model = model_of(_ORIGIN, make_owner("1"), make_owner("4"), make_item("2"))
    stored = dict(to_data(model))
    stored["schema_version"] = 1
    with pytest.raises(SchemaVersionError) as excinfo:
        from_data(stored)
    assert (excinfo.value.expected, excinfo.value.actual) == (SCHEMA_VERSION, 1)
    assert f"version {SCHEMA_VERSION}" in str(excinfo.value)
    assert "not 1" in str(excinfo.value)


def test_the_version_is_checked_before_the_rest_is_looked_at() -> None:
    """A future file with a different layout is reported as a version, not as missing keys."""
    with pytest.raises(SchemaVersionError):
        _read({"schema_version": 99, "somethings": "new"})


@pytest.mark.parametrize("key", ["aliases", "tables"])
def test_a_missing_top_level_key_is_a_schema_error(key: str) -> None:
    """`to_data` writes every key, so every key is required."""
    data = _base()
    del data[key]
    with pytest.raises(SchemaError, match=key):
        _read(data)


def test_an_extra_top_level_key_is_a_schema_error() -> None:
    """A future field bumps the version instead of sneaking in."""
    data = _base()
    data["surprise"] = 1
    with pytest.raises(SchemaError, match="surprise") as excinfo:
        _read(data)
    assert excinfo.value.kind == "canonical"


def test_tables_must_be_a_mapping_of_arrays_of_mappings() -> None:
    """Each shape of the envelope is checked before any record is built."""
    for broken in ({"tables": []}, {"tables": {"k": {}}}, {"tables": {"k": [3]}}):
        data = {**_base(), **broken}
        with pytest.raises(SchemaError) as excinfo:
            _read(data)
        assert excinfo.value.kind == "canonical"


@pytest.mark.parametrize(
    "alias",
    [["only-one"], "not-a-pair", [1, 2], ["a:1", "b:2", "c:3"]],
    ids=["one", "str", "ints", "three"],
)
def test_an_alias_entry_must_be_a_pair_of_strings(alias: Any) -> None:
    """A malformed alias entry has no record either, so it raises directly."""
    data = _base()
    data["aliases"] = [alias]
    with pytest.raises(SchemaError, match="alias") as excinfo:
        _read(data)
    assert excinfo.value.kind == "canonical"


def test_an_unknown_kind_is_collected_in_a_freeze_error() -> None:
    """Per-record problems are gathered, so an author fixes a batch."""
    data = _base()
    data["tables"]["no_such_kind"] = [{}]
    (error,) = _errors_of(data)
    assert isinstance(error, SchemaError)
    assert "no_such_kind" in str(error)


def test_an_unknown_field_is_reported_by_name() -> None:
    """A field the kind does not have is an error, not something to drop."""
    data = _base()
    _item(data)["surprise"] = 1
    (error,) = _errors_of(data)
    assert isinstance(error, SchemaError)
    assert "unknown fields ['surprise']" in str(error)
    assert "missing fields []" in str(error)
    assert error.kind == "canon_item_probe"


def test_a_missing_field_is_reported_by_name() -> None:
    """Every field is written, so a missing one is an error, not a default."""
    data = _base()
    del _item(data)["name"]
    (error,) = _errors_of(data)
    assert isinstance(error, SchemaError)
    assert "missing fields ['name']" in str(error)
    assert "unknown fields []" in str(error)
    assert error.kind == "canon_item_probe"


def test_a_bad_nested_value_reports_its_own_class_name_as_kind() -> None:
    """decode.py:208: a nested `@value`'s own class name is the kind, not the record's.

    `_fields` is called again for `CanonDetail`, so its `SchemaError.kind` is
    `"CanonDetail"`, carried unchanged through `_field` (:173) and `_fill` (:129) to the
    error `_errors_of` sees.
    """
    data = _base()
    _item(data)["details"] = [
        {
            "amount": "1.5",
            "owner": "canon_owner_probe:" + "1" * 32,
            "shade": None,
            "surprise": 1,
        }
    ]
    (error,) = _errors_of(data)
    assert isinstance(error, SchemaError)
    assert error.kind == "CanonDetail"


@pytest.mark.parametrize(
    ("field", "broken", "phrase", "expected_kind"),
    [
        ("owner", "not-an-id", "field `owner`: 'not-an-id' is not `kind:value`", "id"),
        ("shade", "green", "field `shade`: 'green' is not a member of Shade", "canonical"),
        ("amount", "abc", "field `amount`: 'abc' is not a decimal number", "canonical"),
        ("level", 99, "field `level`: 99 is not a member of Level", "canonical"),
        ("level", True, "field `level`: True is not a member of Level", "canonical"),
        ("amount", " 1", "not in canonical form", "canonical"),
        ("amount", "1_0", "not in canonical form", "canonical"),
        ("amount", "١٢٣", "not in canonical form", "canonical"),
        ("amount", "1.50", "is not in canonical form, which is '1.5'", "canonical"),
        ("amount", "1E+3", "is not in canonical form, which is '1000'", "canonical"),
        ("amount", "-0", "is not in canonical form, which is '0'", "canonical"),
    ],
    ids=[
        "id-text",
        "enum-value",
        "decimal-text",
        "int-enum-value",
        "bool-for-int-enum",
        "decimal-space",
        "decimal-underscore",
        "decimal-arabic-digits",
        "decimal-trailing-zero",
        "decimal-exponent",
        "decimal-negative-zero",
    ],
)
def test_text_that_does_not_convert_is_collected_with_its_field(
    field: str, broken: Any, phrase: str, expected_kind: str
) -> None:
    """A bad id, an enum value that is not a member, a `Decimal` that does not parse.

    `expected_kind` pins decode.py:173's `kind=exc.kind`: `"id"` comes from `ids.parse_id`
    unchanged, everything else is decode's own `_KIND` (`"canonical"`).
    """
    data = _base()
    _item(data)[field] = broken
    (error,) = _errors_of(data)
    assert isinstance(error, SchemaError)
    assert phrase in str(error)
    assert error.kind == expected_kind


@pytest.mark.parametrize(
    "ext",
    [
        {"x": {"$oops": 1}},
        {"x": {"$map": 1}},
        {"x": {"$map": {}, "$id": "a:1"}},
        {"x": {"a": 1}},
        {"x": {}},
    ],
    ids=["unknown-tag", "map-not-a-mapping", "two-tags", "untagged-mapping", "empty-mapping"],
)
def test_a_mapping_at_an_undeclared_position_must_be_exactly_one_known_tag(ext: Any) -> None:
    """Under `ext` a JSON object is `$map` or `$id`, nothing else."""
    data = _base()
    _item(data)["ext"] = ext
    (error,) = _errors_of(data)
    assert isinstance(error, SchemaError)
    assert error.kind == "canonical"


def test_a_wrong_json_type_is_left_for_freeze_to_report_with_its_path() -> None:
    """The decoder converts only what it must; `conform` reports a string where an int is due."""
    data = _base()
    _item(data)["count"] = "3"
    (error,) = _errors_of(data)
    assert isinstance(error, SchemaError)
    assert "count" in str(error)
    assert error.record_id == item_id("2")


def test_a_records_own_rule_refusing_arrives_inside_the_freeze_error() -> None:
    """kernel-records.md: a `__post_init__` refusal in `from_data` is a `SchemaError`."""
    owner = make_freeze_owner("1")
    pair = Pair(
        id=Id(kind="freeze_pair_probe", value="3" * 32),
        key=("p",),
        first=owner.id,
        second=make_freeze_owner("2").id,
    )
    text = dumps(freeze(draft_of(_ORIGIN, owner, make_freeze_owner("2"), pair)))
    data = json.loads(text)
    record = data["tables"]["freeze_pair_probe"][0]
    record["second"] = record["first"]
    (error,) = _errors_of(data)
    assert isinstance(error, SchemaError)
    assert "two different owners" in str(error)


def test_two_different_records_with_one_id_are_a_conflict_not_a_silent_choice() -> None:
    """Duplicate ids in the data go through `Draft.add`, so nothing wins silently."""
    data = _base()
    table = data["tables"]["canon_owner_probe"]
    twin = deepcopy(table[0])
    twin["ext"] = {"different": 1}
    table.append(twin)
    (error,) = _errors_of(data)
    assert isinstance(error, MergeConflict)


def test_an_identical_duplicate_in_the_data_is_harmless() -> None:
    """Saying the same thing twice is a no-op, as in a `Draft`."""
    data = _base()
    table = data["tables"]["canon_owner_probe"]
    table.append(deepcopy(table[0]))
    assert _read(data) == _read(_base())


def test_every_bad_record_is_reported_not_just_the_first() -> None:
    """Two problems in two records give two errors in one `FreezeError`."""
    data = _base()
    _item(data)["owner"] = "not-an-id"
    data["tables"]["no_such_kind"] = [{}]
    assert len(_errors_of(data)) == 2


def test_an_alias_to_an_id_nobody_holds_is_a_freeze_error() -> None:
    """Aliases are handed to `Draft.alias`, so `freeze` rejects one that leads nowhere."""
    data = _base()
    data["aliases"] = [["canon_owner_probe:" + "8" * 32, "canon_owner_probe:" + "9" * 32]]
    (error,) = _errors_of(data)
    assert isinstance(error, RefError)


def test_an_alias_that_the_draft_refuses_is_collected() -> None:
    """An alias of an id to itself is refused by `Draft.alias` and reported, not raised raw."""
    data = _base()
    same = "canon_owner_probe:" + "1" * 32
    data["aliases"] = [[same, same]]
    (error,) = _errors_of(data)
    assert isinstance(error, SchemaError)


@pytest.mark.parametrize(
    ("text", "phrase"),
    [
        ("{", "not valid JSON"),
        ('{"a": 1, "a": 2}', "duplicate"),
        ('{"schema_version": 1.5}', "number"),
        ('{"schema_version": NaN}', "not canonical"),
        ('{"schema_version": 1e3}', "number"),
    ],
    ids=["syntax", "duplicate-key", "float", "nan", "exponent"],
)
def test_json_that_is_not_canonical_is_a_schema_error_not_a_stdlib_error(
    text: str, phrase: str
) -> None:
    """Syntax errors, repeated keys, floats and NaN are refused as `SchemaError`."""
    with pytest.raises(SchemaError, match=phrase):
        loads(text)


def test_a_large_integer_is_kept_exactly() -> None:
    """Integers are arbitrary precision in JSON and in Python: nothing is rounded."""
    data = _base()
    _item(data)["count"] = 10**40
    assert _read(data).tables["canon_item_probe"][item_id("2")].count == 10**40


def test_loading_does_not_depend_on_the_order_of_keys_or_records_in_the_text() -> None:
    """Records may arrive in any order; the model, and its dump, are the same."""
    data = _base()
    data["tables"]["canon_owner_probe"].reverse()
    shuffled = json.dumps(data, sort_keys=False)
    assert loads(shuffled) == _read(_base())
    assert dumps(loads(shuffled)) == dumps(_read(_base()))


def test_the_owner_ids_in_the_base_are_what_the_tests_assume() -> None:
    """A guard on the fixture: the corruptions refer to owners `1` and `4`."""
    ids = {entry["id"] for entry in _base()["tables"]["canon_owner_probe"]}
    assert ids == {"canon_owner_probe:" + "1" * 32, "canon_owner_probe:" + "4" * 32}
    assert owner_id("1") in _read(_base()).tables["canon_owner_probe"]


def test_a_number_with_too_many_digits_is_a_schema_error_not_a_value_error() -> None:
    """CPython refuses a very long int; `loads` says so as a `SchemaError`."""
    text = json.dumps(_base()).replace('"count": 3', '"count": ' + "1" * 5000)
    with pytest.raises(SchemaError, match="5000 characters"):
        loads(text)


def test_an_int_over_the_bit_limit_is_reported_by_freeze_with_its_field() -> None:
    """A long but readable int reaches `freeze()`, whose `check_value` names the field."""
    text = json.dumps(_base()).replace('"count": 3', '"count": ' + "1" * 700)
    with pytest.raises(FreezeError) as excinfo:
        loads(text)
    (error,) = excinfo.value.errors
    assert "count" in str(error)
    assert "bits" in str(error)


def test_deeply_nested_json_is_a_schema_error_not_a_recursion_error() -> None:
    """The parser and the thaw both recurse; neither may leak `RecursionError`."""
    with pytest.raises(SchemaError, match="nested too deeply"):
        loads("[" * 5000 + "]" * 5000)


def test_deeply_nested_data_is_a_schema_error_not_a_recursion_error() -> None:
    """`from_data` takes data that never went through the JSON parser."""
    nested: Any = ()
    for _ in range(5000):
        nested = (nested,)
    data = _base()
    _item(data)["ext"] = {"x": nested}
    with pytest.raises(SchemaError, match="nested too deeply") as excinfo:
        from_data(data)
    assert excinfo.value.kind == "canonical"


def _derived_data() -> dict[str, Any]:
    model = model_of(_ORIGIN, CanonDerived(id=derived_id("5"), key=("5",), name="pump"))
    return json.loads(dumps(model))


def test_a_derived_field_is_not_read_back_from_the_data() -> None:
    """`shout` is `init=False`: the record derives it, so a tampered value changes nothing."""
    data = _derived_data()
    data["tables"]["canon_derived_probe"][0]["shout"] = "tampered"
    reloaded = _read(data).tables["canon_derived_probe"][derived_id("5")]
    assert reloaded.shout == "PUMP"


def test_a_derived_field_must_still_be_present() -> None:
    """Every field is written, so a missing one means the data was not written by `dumps`."""
    data = _derived_data()
    del data["tables"]["canon_derived_probe"][0]["shout"]
    (error,) = _errors_of(data)
    assert "missing fields ['shout']" in str(error)


@pytest.mark.parametrize(
    ("text", "phrase"),
    [
        ("NaN", "Decimal NaN is not finite"),
        ("sNaN", "Decimal sNaN is not finite"),
        ("Infinity", "Decimal Infinity is not finite"),
        ("1e999999999", "exponent beyond 1000"),
    ],
)
def test_a_decimal_freeze_refuses_is_reported_by_freeze_with_its_field(
    text: str, phrase: str
) -> None:
    """Readable as a `Decimal` but not a quantity: the decoder leaves it to `check_value`."""
    data = _base()
    _item(data)["amount"] = text
    (error,) = _errors_of(data)
    assert isinstance(error, ValueTypeError)
    assert phrase in str(error)
    assert error.record_id == item_id("2")


def test_an_authoring_key_field_decodes_through_the_alias_not_a_shortcut() -> None:
    """decode.py:179: `AuthoringKey` must be unwrapped to `tuple[str, ...]` before deciding
    how to walk the value; skipping the unwrap sends it through `_decode_undeclared`
    instead (B3, mutmut report).

    A plain list of strings comes back a tuple either way, so it cannot tell the two
    paths apart. A `$id`-tagged mapping does: under the real `tuple[str, ...]` item
    annotation (`str`) it is left untouched for `freeze()` to reject as the wrong type;
    under the undeclared fallback it is silently turned into an `Id`.
    """
    annotation = key_and_value_aliases()[0]
    tagged = {"$id": "canon_owner_probe:" + "1" * 32}
    result = _decode_value(["a", tagged], annotation)
    assert result == ("a", tagged)
    assert type(result) is tuple
    assert isinstance(result[1], dict)


@pytest.mark.parametrize("value", [42, {"a": 1}], ids=["int", "dict"])
def test_a_non_str_value_for_an_id_field_passes_through_unchanged(value: Any) -> None:
    """decode.py:189: only a `str` is handed to `parse_id`; anything else is left for
    `freeze()` to reject with a proper path, never reaching `parse_id` (B4, mutmut report).
    """
    result = _decode_value(value, Id[Any])
    assert result is value


def test_a_non_str_id_value_reaches_freezes_schema_check_through_the_full_pipeline() -> None:
    """B4's own wording, through the public `loads`/`from_data`/`freeze()` pipeline: a JSON
    number in an `owner: Id[Owner]` field never reaches `parse_id` (which would crash on a
    non-str), and is instead refused by `freeze()`'s schema check.
    """
    data = _base()
    _item(data)["owner"] = 42
    (error,) = _errors_of(data)
    assert isinstance(error, SchemaError)
    assert error.record_id == item_id("2")


@pytest.mark.parametrize("annotation", [str, int, bool, None], ids=["str", "int", "bool", "none"])
def test_a_dict_under_a_plain_annotation_passes_through_undecoded(annotation: Any) -> None:
    """decode.py:214: a `dict` given where `str`/`int`/`bool`/`None` is declared is left
    alone, not walked as an undeclared value (B5, mutmut report).
    """
    value = {"a": 1}
    result = _decode_plain(value, annotation)
    assert result is value


@pytest.mark.parametrize("sign", ["+", "-"])
def test_a_decimal_at_the_exponent_limit_still_checks_canonical_form(sign: str) -> None:
    """decode.py:246: at exactly `MAX_EXPONENT` the guard must be false, so a non-canonical
    text (scientific notation) still reaches the canonical-form check and is refused (B6,
    mutmut report: `>` mutated to `>=` would skip this check at the boundary itself).
    """
    text = f"1E{sign}{MAX_EXPONENT}"
    with pytest.raises(SchemaError, match="not in canonical form") as excinfo:
        _decimal(text)
    assert excinfo.value.kind == "canonical"


def test_a_decimal_at_the_exponent_limit_in_canonical_form_is_accepted() -> None:
    """The literal accepted case: a canonical text at exactly `MAX_EXPONENT` decodes with
    no error at all.
    """
    text = "1" + "0" * MAX_EXPONENT
    assert _decimal(text) == Decimal(text)


@pytest.mark.parametrize("sign", ["+", "-"])
def test_a_decimal_beyond_the_exponent_limit_skips_the_canonical_check(sign: str) -> None:
    """One past `MAX_EXPONENT`, the guard returns the number without ever computing
    `decimal_text` (which would spell it out digit by digit): the same non-canonical text
    that decode.py:246 refuses at the limit is accepted here, because refusing an absurd
    exponent is `freeze()`'s job, not decode's (the comment on :245).
    """
    text = f"1E{sign}{MAX_EXPONENT + 1}"
    assert _decimal(text) == Decimal(text)


@pytest.mark.parametrize("sign", ["+", "-"])
def test_a_decimal_beyond_the_exponent_limit_is_refused_downstream_by_freeze(sign: str) -> None:
    """The full pipeline: decode lets a beyond-limit `Decimal` through unchecked, and
    `freeze()`'s `check_value` is what actually refuses it, as `ValueTypeError`, with the
    field's path -- not `SchemaError` (decode.py never raises for this case; see the two
    tests above).
    """
    data = _base()
    _item(data)["amount"] = f"1E{sign}{MAX_EXPONENT + 1}"
    (error,) = _errors_of(data)
    assert isinstance(error, ValueTypeError)
    assert "exponent beyond" in str(error)
    assert error.path == ("amount",)
    assert error.record_id == item_id("2")
