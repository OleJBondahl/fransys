"""`derive.release_rows` and `derive.release_previous`: release facts over a model or a store.

The stored releases are hand-built `Listing`s here; the facade's folder fill is tested from the
repository root (`tests/test_stored_release.py`).
"""

from fransys_model.derive import pin_source, previous_release
from fransys_model.derive.baseline import ReleaseIdentity, StoredRelease, StoredReleases
from fransys_model.derive.numbering_pins import NumberingPins
from fransys_model.derive.release_rows import _libraries
from fransys_model.derive.rows_baseline import BaselineUnit, Listing, ManifestLibrary


def _stored(version, revision, *, name="u", numbering=True):
    unit = BaselineUnit(name=name, version=version, revision=revision, interface="1")
    listing = Listing(unit=unit, items=(), units=(), boundary=(), conductors=(), mates=(), nets=())
    pins = NumberingPins(items=(), retired=()) if numbering else None
    return StoredRelease(folder=f"{version}.{revision}", listing=listing, numbering=pins)


def _folder(release):
    return None if release is None else release.folder


def _identity(version, revision, name="u"):
    return ReleaseIdentity(name=name, version=version, revision=revision, interface="1")


def test_previous_release_is_strictly_below_across_versions():
    stored = StoredReleases(releases=(_stored(1, 1), _stored(1, 9), _stored(2, 1), _stored(2, 3)))
    assert _folder(previous_release(stored, _identity(2, 3))) == "2.1"
    assert _folder(previous_release(stored, _identity(2, 1))) == "1.9"
    assert previous_release(stored, _identity(1, 1)) is None


def test_previous_release_never_picks_its_own_folder():
    stored = StoredReleases(releases=(_stored(1, 1), _stored(1, 2)))
    assert _folder(previous_release(stored, _identity(1, 2))) == "1.1"


def test_pin_source_is_same_version_at_or_below_with_numbering():
    stored = StoredReleases(
        releases=(_stored(1, 1), _stored(1, 2, numbering=False), _stored(1, 3), _stored(2, 1))
    )
    assert _folder(pin_source(stored, _identity(1, 3))) == "1.3"
    assert _folder(pin_source(stored, _identity(1, 2))) == "1.1"
    assert _folder(pin_source(stored, _identity(2, 1))) == "2.1"
    assert pin_source(stored, _identity(3, 1)) is None
    assert pin_source(stored, _identity(1, 3, name="other")) is None


def test_libraries_skip_a_part_authored_in_python():
    """`release_rows._libraries` (manifest `part_libraries`, L3): a `Part` with no `library` --
    `Part.library`'s own docstring: `None` for one "authored in Python", never sourced from a
    loaded part-file library, a shape `fransys_author` itself never produces today but the
    model schema allows and this reader must still handle -- contributes no entry, while a
    real, library-sourced part's does. Hand-built model (no `fr.build`/`fransys_author`, the same
    pattern `tests/test_units_worked_example.py`'s cross-unit probe uses): this is the only
    way to construct a `Part` with `library=None` at all.
    """
    from fransys_model.kernel import Draft, Origin, freeze, make_id
    from fransys_model.vocab.core import Item
    from fransys_model.vocab.enums import PartCategory
    from fransys_model.vocab.templates import Part, PartLibrary

    library_key = ("part_library", "demo-parts")
    library = PartLibrary(
        id=make_id(PartLibrary, library_key), key=library_key, name="demo-parts", version="0.1.0"
    )
    with_lib_key = ("part", "Demo", "WITH-LIB")
    with_lib = Part(
        id=make_id(Part, with_lib_key),
        key=with_lib_key,
        mpn="WITH-LIB",
        manufacturer="Demo",
        description="a library-sourced part",
        category=PartCategory.GENERIC,
        class_code="Z",
        library=library.id,
    )
    no_lib_key = ("part", "Demo", "NO-LIB")
    no_lib = Part(
        id=make_id(Part, no_lib_key),
        key=no_lib_key,
        mpn="NO-LIB",
        manufacturer="Demo",
        description="a part authored in Python, no library",
        category=PartCategory.GENERIC,
        class_code="Z",
        library=None,
    )
    with_lib_item_key = ("item", "z1")
    with_lib_item = Item(
        id=make_id(Item, with_lib_item_key),
        key=with_lib_item_key,
        part=with_lib.id,
        parent=None,
        position=None,
        tag="Z1",
        description="",
    )
    no_lib_item_key = ("item", "z2")
    no_lib_item = Item(
        id=make_id(Item, no_lib_item_key),
        key=no_lib_item_key,
        part=no_lib.id,
        parent=None,
        position=None,
        tag="Z2",
        description="",
    )
    draft = Draft()
    draft.extend(
        (library, with_lib, no_lib, with_lib_item, no_lib_item),
        origin=Origin(file="<probe>", line=1, note="Part.library=None"),
    )
    model = freeze(draft)

    assert _libraries(model, None) == (ManifestLibrary(name="demo-parts", version="0.1.0"),)
