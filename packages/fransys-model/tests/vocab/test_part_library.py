"""Tests for `PartLibrary`, `Part.library` and `check_part_library` (design/vocabulary.md 6, 7)."""

import pytest

from fransys_model.kernel import (
    Draft,
    FreezeError,
    Id,
    MergeConflict,
    Model,
    Origin,
    Record,
    dumps,
    freeze,
    loads,
    make_id,
)
from fransys_model.vocab import ALL_VALIDATORS, part_libraries
from fransys_model.vocab.enums import PartCategory
from fransys_model.vocab.templates import Part, PartLibrary
from fransys_model.vocab.validators.part_library import (
    PART_LIBRARY_VERSION_CONFLICT,
    check_part_library,
)

_ORIGIN = Origin(file="test_part_library.py", line=1, note="fixture")


def _library(name: str, version: str, *, key_name: str | None = None) -> PartLibrary:
    key = ("part_library", key_name or name)
    return PartLibrary(id=make_id(PartLibrary, key), key=key, name=name, version=version)


def _part(library: Id[PartLibrary] | None, name: str = "relay") -> Part:
    key = (name,)
    return Part(
        id=make_id(Part, key),
        key=key,
        mpn="EXAMPLE-RELAY-1",
        manufacturer="Example Co",
        description="Invented example relay",
        category=PartCategory.ELECTROMECHANICAL,
        class_code="K",
        library=library,
    )


def _freeze(*records: Record) -> Model:
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def test_part_library_carries_name_and_version_under_the_designed_key() -> None:
    """A library keyed `("part_library", name)` holds its name and version, and only those."""
    library = _library("invented-parts", "1.4.0")
    model = _freeze(library)
    assert part_libraries(model)[library.id] == library
    assert library.key == ("part_library", "invented-parts")
    assert (library.name, library.version) == ("invented-parts", "1.4.0")


def test_part_library_defaults_to_none_for_a_part_authored_in_python() -> None:
    """`Part.library` is `None` unless a part library supplied the part."""
    assert _part(None).library is None


def test_part_points_at_its_library_and_round_trips_through_canonical_form() -> None:
    """The reference survives `dumps`/`loads`, and the model digest follows the version."""
    library = _library("invented-parts", "1.4.0")
    model = _freeze(library, _part(library.id))
    assert loads(dumps(model)) == model
    newer = _freeze(_library("invented-parts", "1.5.0"), _part(library.id))
    assert newer.digest != model.digest


def test_part_referring_to_a_missing_library_is_a_freeze_error() -> None:
    """A dangling `Part.library` fails at `freeze()`, as any reference does."""
    with pytest.raises(FreezeError):
        _freeze(_part(make_id(PartLibrary, ("part_library", "absent"))))


def test_part_referring_to_a_record_of_another_kind_is_a_freeze_error() -> None:
    """`Part.library` names one kind: an id of a `part` is refused."""
    other = _part(None, "fuse")
    with pytest.raises(FreezeError):
        _freeze(other, _part(Id(kind="part", value=other.id.value)))


def test_the_key_rule_refuses_one_name_with_two_versions_at_the_draft() -> None:
    """Records built through `make_id` share an id per name, so a second version cannot be added."""
    draft = Draft()
    draft.add(_library("invented-parts", "1.4.0"), origin=_ORIGIN)
    with pytest.raises(MergeConflict):
        draft.add(_library("invented-parts", "1.5.0"), origin=_ORIGIN)


def test_two_libraries_of_one_name_and_version_are_no_conflict() -> None:
    """The same name and version twice is one fact repeated, not two versions."""
    twin = _library("invented-parts", "1.4.0", key_name="other-key")
    model = _freeze(_library("invented-parts", "1.4.0"), twin)
    assert check_part_library(model) == ()


def test_libraries_of_different_names_are_no_conflict() -> None:
    """Different names may carry different versions."""
    model = _freeze(_library("invented-parts", "1.4.0"), _library("invented-cables", "2.0.0"))
    assert check_part_library(model) == ()


def test_one_name_with_two_versions_under_hand_made_keys_yields_a_conflict() -> None:
    """`freeze()` does not re-derive ids from keys, so a hand-keyed pair reaches the validator."""
    old = _library("invented-parts", "1.4.0")
    new = _library("invented-parts", "1.5.0", key_name="hand-made")
    (finding,) = check_part_library(_freeze(old, new))
    assert finding.code == PART_LIBRARY_VERSION_CONFLICT
    assert set(finding.subjects) == {old.id, new.id}
    assert finding.message == "part library invented-parts is recorded with versions 1.4.0, 1.5.0"


def test_three_versions_of_one_name_are_one_finding_and_other_names_stay_clean() -> None:
    """One finding per name, whatever the number of versions; an unrelated name adds none."""
    records = (
        _library("invented-parts", "1.0.0", key_name="a"),
        _library("invented-parts", "1.1.0", key_name="b"),
        _library("invented-parts", "1.2.0", key_name="c"),
        _library("invented-cables", "2.0.0"),
    )
    assert len(check_part_library(_freeze(*records))) == 1


def test_findings_do_not_depend_on_the_order_records_were_added() -> None:
    """The validator reads a table, so the order of `add` cannot show in its result."""
    records = (
        _library("invented-parts", "1.4.0"),
        _library("invented-parts", "1.5.0", key_name="hand-made"),
        _library("invented-cables", "2.0.0"),
        _library("invented-cables", "2.1.0", key_name="hand-made-too"),
    )
    assert check_part_library(_freeze(*records)) == check_part_library(_freeze(*reversed(records)))


def test_the_validator_is_part_of_all_validators() -> None:
    """`ALL_VALIDATORS` runs `check_part_library`, so a caller running them all sees the finding."""
    assert check_part_library in ALL_VALIDATORS
