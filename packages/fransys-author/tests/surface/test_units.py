"""EA8 first half: `@unit` and `d.add` build a child design that carries its unit release."""

from typing import NamedTuple

import fransys_author
import pytest
from fransys_author import AuthorError
from fransys_author import surface as surface_module
from fransys_author.surface import Design, Device, design, unit

from fransys_model.kernel import freeze, merge
from fransys_model.vocab import Boundary, Mate, Revision, Unit, UnitRelease, UnusedBoundary
from fransys_model.vocab import Item as ModelItem
from fransys_model.vocab.validators.units import BOUNDARY_UNCONNECTED, check_units

from ..equivalence.series_parts import pair_library  # noqa: TID252 -- importlib mode puts tests/ on no path

_OLD = {"revision": 1, "date": "2026-01-01", "text": "first", "created": "AA"}


class _Pair(NamedTuple):
    X1: Device
    X2: Device


class _One(NamedTuple):
    X1: Device


class _Nothing(NamedTuple):
    pass


@unit("demo-io-board", revision=2, interface_version=1, date="2026-02-02", text="second", by="XX")
def io_board(d: Design) -> _Pair:
    x1 = d.device("X1", "DEMO-CONN-2P", interface=True)
    x2 = d.device("X2", "DEMO-CONN-2P", interface=True)
    return _Pair(x1, x2)


def _records(d, cls):
    return [r for r in d.draft().records() if isinstance(r, cls)]


def test_the_child_carries_the_unit_release_and_its_items() -> None:
    d = design(pair_library())
    d.add(io_board, "IO")
    (release,) = _records(d, UnitRelease)
    (model_unit,) = _records(d, Unit)
    assert (release.name, release.revision, release.interface) == ("demo-io-board", 2, "1")
    assert model_unit.release == release.id
    assert {i.unit for i in _records(d, ModelItem)} == {model_unit.id}


def test_a_name_gives_the_boundary_device() -> None:
    io = design(pair_library()).add(io_board, "IO")
    assert io.X1._label == "X1"
    assert io.X1 is not io.X2


def test_history_entries_are_written_before_the_own_entry() -> None:
    @unit(
        "demo-io-board",
        revision=2,
        interface_version=1,
        date="d2",
        text="t2",
        by="XX",
        history=[_OLD],
    )
    def board(_d: Design) -> _Nothing:
        return _Nothing()

    d = design(pair_library())
    d.add(board, "IO")
    revisions = {r.revision: r for r in _records(d, Revision)}
    assert revisions[1].text == "first"
    assert (revisions[2].text, revisions[2].created) == ("t2", "XX")


@pytest.mark.parametrize("made", ["list", "dict", "tuple"])
def test_a_return_that_is_no_named_tuple_raises_and_shows_the_form(made: str) -> None:
    @unit("demo-io-board", revision=1, interface_version=1, date="d", text="t", by="XX")
    def board(d):
        x1 = d.device("X1", "DEMO-CONN-2P")
        return {"list": [x1], "dict": {"X1": x1}, "tuple": (x1,)}[made]

    with pytest.raises(AuthorError, match=r"must return an instance of a typing.NamedTuple.*Io\("):
        design(pair_library()).add(board, "IO")


def test_a_second_add_of_one_name_raises() -> None:
    d = design(pair_library())
    d.add(io_board, "IO")
    with pytest.raises(AuthorError, match="already used"):
        d.add(io_board, "IO")


def test_unit_is_on_the_surface_and_off_the_package_root() -> None:
    assert "unit" in surface_module.__all__
    assert "AddedUnit" not in surface_module.__all__
    assert "unit" not in fransys_author.__all__


# --- U2: the boundary marks and the parent's mate ---


def _unconnected(d):
    model = freeze(merge(pair_library(), d.draft()))
    return [f for f in check_units(model) if f.code == BOUNDARY_UNCONNECTED]


def _cabinet(*, mate: bool, unused: bool = False):
    @unit("demo-io-board", revision=1, interface_version=1, date="d", text="t", by="XX")
    def board(d: Design) -> _One:
        x1 = d.device("X1", "DEMO-CONN-2P", interface=True)
        if unused:
            d.device("X2", "DEMO-CONN-2P", unused=True)
        return _One(x1)

    d = design(pair_library(), place="C1")
    io = d.add(board, "IO")
    p1 = d.device("P1", "DEMO-CONN-2P")  # outside the unit: the unit is not standalone
    if mate:
        d.mate(p1, io.X1)
    return d


def test_interface_and_unused_write_the_boundary_records() -> None:
    d = _cabinet(mate=True, unused=True)
    assert len(_records(d, Boundary)) == 2
    assert len(_records(d, UnusedBoundary)) == 1
    assert len(_records(d, Mate)) == 1


def test_a_boundary_neither_mated_nor_unused_gives_the_engine_finding() -> None:
    (found,) = _unconnected(_cabinet(mate=False))
    assert "has no declared UnusedBoundary" in found.message


def test_a_mated_boundary_gives_no_boundary_finding() -> None:
    assert _unconnected(_cabinet(mate=True)) == []


def test_an_unused_boundary_alone_is_the_only_one_flagged() -> None:
    (found,) = _unconnected(_cabinet(mate=False, unused=True))
    assert "X1" in found.message
    assert "X2" not in found.message


def _one_device_unit(**marks):
    @unit("demo-io-board", revision=1, interface_version=1, date="d", text="t", by="XX")
    def board(d: Design) -> _One:
        return _One(d.device("X2", "DEMO-CONN-2P", **marks))

    d = design(pair_library(), place="C1")
    d.add(board, "IO")
    return d


def test_unused_alone_makes_a_boundary_and_silences_it() -> None:
    d = _one_device_unit(unused=True)
    assert len(_records(d, Boundary)) == 1
    assert len(_records(d, UnusedBoundary)) == 1


def test_interface_with_unused_writes_one_boundary_and_one_unused() -> None:
    d = _one_device_unit(interface=True, unused=True)
    assert len(_records(d, Boundary)) == 1
    assert len(_records(d, UnusedBoundary)) == 1


@pytest.mark.parametrize("tag", ["-U1", "+U1", "=U1"])
def test_a_unit_tag_with_a_prefix_raises(tag: str) -> None:
    with pytest.raises(AuthorError, match=r"^write U1; add\(\) adds the -$"):
        design(pair_library()).add(io_board, tag)


def test_a_plain_unit_name_still_adds() -> None:
    assert design(pair_library()).add(io_board, "IO").X1 is not None


def test_the_release_argument_is_interface_version_not_interface() -> None:
    with pytest.raises(TypeError, match=r"unexpected keyword argument .interface."):
        unit(
            "demo-io-board",
            revision=1,
            interface_version=1,
            interface=1,  # ty: ignore[unknown-argument] -- the refusal under test
            date="d",
            text="t",
            by="XX",
        )
