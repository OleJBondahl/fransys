"""The signature walk of A8: no public callable takes a coordinate, page or column (A-r5).

Every public callable of `Design`, `Scope` and the handle types is walked; a parameter
named like a geometry concept, or annotated with a geometry type, fails the walk.
`position` and `index` are legitimate build facts (rail slot, terminal position), not
coordinates, and stay off the forbidden list.
"""

import annotationlib
import inspect

import fransys_author
from fransys_author import (
    Cable,
    Design,
    Fn,
    Group,
    Item,
    Location,
    Port,
    Scope,
    Strip,
    Terminal,
    Wiring,
)

_FORBIDDEN_NAMES = frozenset(
    {"x", "y", "page", "column", "row", "page_number", "column_number", "row_number", "points"}
)
_FORBIDDEN_ANNOTATION_WORDS = ("point", "coordinate")
# Not forbidden: `Project.number` (a project number like "P-1001", spec A2) is a business
# field, not a layout page number; `position`/`index` are build facts (design/layout-namespace.md
# already excludes only x/y/page/number/points from the *model's* authored-kind fields -- this is
# the author API's own, narrower list, since the API also carries `Project.number`).
# `__call__` (the wire maker) and `__getitem__` (port-by-marking) are genuine public API
# surfaces reached through operator syntax; every other dunder is implementation detail.
_DUNDER_ALLOWLIST = frozenset({"__call__", "__getitem__"})

_WALKED_TYPES = (Design, Scope, Cable, Fn, Group, Item, Location, Port, Strip, Terminal, Wiring)


def _public_callables(cls: type) -> list[tuple[str, str, inspect.Signature]]:
    """Every public callable `cls` offers, including what it inherits (`Design` from `Scope`)."""
    found = []
    for name in dir(cls):
        if name not in _DUNDER_ALLOWLIST and name.startswith("_"):
            continue
        member = inspect.getattr_static(cls, name)
        if isinstance(member, property):
            member = member.fget
        if member is None or not callable(member):
            continue
        try:
            # STRING format: reads annotations as their source text, without evaluating
            # them -- most of this package's annotations are TYPE_CHECKING-only names
            # (ruff TC003/TC002), so evaluating them would raise NameError for real code.
            signature = inspect.signature(member, annotation_format=annotationlib.Format.STRING)
        except TypeError, ValueError:
            continue
        found.append((cls.__name__, name, signature))
    return found


def _violations(owner: str, name: str, signature: inspect.Signature) -> list[str]:
    problems = []
    for param_name, param in signature.parameters.items():
        if param_name in ("self", "cls"):
            continue
        if param_name.lower() in _FORBIDDEN_NAMES:
            problems.append(f"{owner}.{name}({param_name}=...): forbidden parameter name")
        annotation = str(param.annotation)
        if any(word in annotation.lower() for word in _FORBIDDEN_ANNOTATION_WORDS):
            problems.append(f"{owner}.{name}({param_name}: {annotation}): forbidden annotation")
    return problems


def test_no_public_callable_takes_a_coordinate_page_or_column():
    problems = [
        problem
        for cls in _WALKED_TYPES
        for owner, name, signature in _public_callables(cls)
        for problem in _violations(owner, name, signature)
    ]
    assert problems == []


def test_public_names_are_exactly_the_ones_the_spec_lists():
    assert set(fransys_author.__all__) == {
        "AuthorError",
        "Cable",
        "Design",
        "Fn",
        "Group",
        "Item",
        "Location",
        "Operating",
        "Port",
        "Rating",
        "Scope",
        "Strip",
        "Terminal",
        "Wiring",
    }


def test_boundary_takes_rating_and_operating_as_keyword_only_values():
    signature = inspect.signature(Scope.boundary, annotation_format=annotationlib.Format.STRING)
    parameters = signature.parameters
    for name in ("rating", "operating"):
        assert parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
        assert parameters[name].default is None


def test_the_walk_can_fail_on_a_deliberately_bad_stub():
    class BadStub:
        def place(self, x: int, y: int) -> None: ...

        def good(self, name: str) -> None: ...

    problems = [
        problem
        for owner, name, signature in _public_callables(BadStub)
        for problem in _violations(owner, name, signature)
    ]
    assert problems == [
        "BadStub.place(x=...): forbidden parameter name",
        "BadStub.place(y=...): forbidden parameter name",
    ]


def test_the_walk_can_fail_on_a_geometry_annotated_stub():
    class Point:
        pass

    class BadStub:
        def move(self, to: Point) -> None: ...

    problems = [
        problem
        for owner, name, signature in _public_callables(BadStub)
        for problem in _violations(owner, name, signature)
    ]
    assert len(problems) == 1
    assert "forbidden annotation" in problems[0]


def test_the_walk_covers_every_callable_the_spec_names():
    """A sample of real, spread-out signatures -- proof the walk reaches deep call sites."""
    found = {(owner, name) for cls in _WALKED_TYPES for owner, name, _ in _public_callables(cls)}
    for owner, name in (
        ("Design", "item"),
        ("Scope", "chain"),
        ("Scope", "draw_in"),
        ("Scope", "rating"),
        ("Scope", "operating"),
        ("Cable", "core"),
        ("Fn", "plc"),
        ("Fn", "scale"),
        ("Item", "fn"),
        ("Strip", "terminal"),
        ("Wiring", "__call__"),
        ("Wiring", "run"),
    ):
        assert (owner, name) in found
