"""EA9 runs: `X3.run(label, count, bridged=)` counts inside its label and a series may name it."""

import pytest
from fransys_author import AuthorError
from fransys_author.surface import design
from fransys_author.surface._strip import Run

from fransys_model.vocab import Conductor, ConductorKind, Port, TerminalFacet

from ..equivalence.series_parts import series_library  # noqa: TID252 -- same suite's stub parts

WIRE = ("BK", 2.5)


@pytest.fixture(scope="module")
def lib():
    return series_library()


def _records(d, cls):
    return [r for r in d.draft().records() if isinstance(r, cls)]


def _facets(d):
    return sorted((f.group, f.index) for f in _records(d, TerminalFacet))


def _wire_terminal_groups(d):
    """The terminal key segment 2 (the group) of every strip port a wire lands on."""
    ports = {p.id: p for p in _records(d, Port)}
    ends = [
        ports[end].key
        for c in _records(d, Conductor)
        if c.kind is ConductorKind.WIRE
        for end in (c.a, c.b)
    ]
    return sorted(key[2] for key in ends if key[:2] == ("X3", "terminal"))


def test_two_runs_count_from_one_independent_of_each_other_and_the_strip(lib) -> None:
    d = design(lib)
    x3 = d.terminal_strip("X3", "TEST-TERM")
    valve = x3.run("valve supply", 3)
    sensor = x3.run("sensors", 2)
    x3._take(2)
    assert isinstance(valve, Run)
    assert _facets(d) == [("", 1), ("", 2), ("sensors", 1), ("sensors", 2)] + [
        ("valve supply", n) for n in (1, 2, 3)
    ]
    assert valve._take(1)[0].key[-2:] == ("valve supply", "1")
    assert sensor._take(1)[0].key[-2:] == ("sensors", "1")


def test_bridged_makes_count_minus_one_jumpers_and_unbridged_none(lib) -> None:
    d = design(lib)
    x3 = d.terminal_strip("X3", "TEST-TERM")
    x3.run("loose", 4)
    assert not _records(d, Conductor)
    x3.run("valve supply", 8, bridged=True)
    kinds = [c.kind for c in _records(d, Conductor)]
    assert kinds == [ConductorKind.JUMPER] * 7


def test_an_overfull_run_names_run_and_count(lib) -> None:
    d = design(lib)
    run = d.terminal_strip("X3", "TEST-TERM").run("valve supply", 2)
    with pytest.raises(
        AuthorError, match=r"X3.run\('valve supply'\) has 2 terminals; the series needs 3"
    ):
        d.series(d.device("Q1", "TEST-MCB-3P").main, run, wire=WIRE)


def test_a_series_on_a_run_lands_in_that_run_only(lib) -> None:
    d = design(lib)
    x3 = d.terminal_strip("X3", "TEST-TERM")
    other = x3.run("sensors", 2)
    run = x3.run("valve supply", 5)
    other._take(2)
    run._take(1)
    d.series(d.device("Q1", "TEST-MCB-3P").main, run, wire=WIRE)
    assert _wire_terminal_groups(d) == ["valve supply"] * 3
    ports = {p.id: p for p in _records(d, Port)}
    numbers = {
        ports[end].key[3]
        for c in _records(d, Conductor)
        for end in (c.a, c.b)
        if ports[end].key[:3] == ("X3", "terminal", "valve supply")
    }
    assert numbers == {"2", "3", "4"}
    assert [t.key[-1] for t in x3._take(2)] == ["1", "2"]


def test_the_runs_pe_part_takes_a_pe_terminal_in_the_run(lib) -> None:
    x3 = design(lib).terminal_strip("X3", "TEST-TERM", pe="TEST-TERM-PE")
    assert x3.run("valve supply", 2)._take_pe().key[-2:] == ("valve supply", "1")


@pytest.mark.parametrize(
    ("label", "count", "match"),
    [
        ("", 2, "label is a non-empty text"),
        (3, 2, "label is a non-empty text"),
        ("a", 0, "count is an integer from 1"),
        ("a", True, "count is an integer from 1"),
        ("a", 2.0, "count is an integer from 1"),
    ],
)
def test_bad_label_or_count_raises(lib, label: object, count: object, match: str) -> None:
    x3 = design(lib).terminal_strip("X3", "TEST-TERM")
    with pytest.raises(AuthorError, match=match):
        x3.run(label, count)  # ty: ignore[invalid-argument-type] -- the test plants the fault


def test_bridged_is_keyword_only_and_a_bool(lib) -> None:
    x3 = design(lib).terminal_strip("X3", "TEST-TERM")
    with pytest.raises(TypeError):
        x3.run("a", 2, True)  # noqa: FBT003 -- planted fault  # ty: ignore[too-many-positional-arguments] -- planted fault
    with pytest.raises(AuthorError, match="bridged is True or False"):
        x3.run("a", 2, bridged=1)  # ty: ignore[invalid-argument-type] -- planted fault


def test_a_duplicate_label_raises_naming_it(lib) -> None:
    x3 = design(lib).terminal_strip("X3", "TEST-TERM")
    x3.run("valve supply", 2)
    with pytest.raises(AuthorError, match="X3 already has a run 'valve supply'"):
        x3.run("valve supply", 3)
    assert design(lib).terminal_strip("X3", "TEST-TERM").run("valve supply", 1)
