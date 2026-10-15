"""Test-local toy record kinds for kernel acceptance tests.

The kernel must not know any engineering term (CLAUDE.md); `Thing` and `Link` are the
fixtures' vocabulary, standing in for whatever `vocab` will later declare with the same
`@record`/`@value` decorators. Exposed as fixtures, pytest's usual sharing mechanism,
rather than imported directly, so test modules need no cross-file import of their own.
"""

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from hypothesis import settings

from fransys_kernel import AuthoringKey, Id, Model, Origin, Record, Value, record, registry, value

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

# --import-mode=importlib leaves this directory off sys.path; tests import helpers by name.
sys.path.append(str(Path(__file__).parent))

# Decision 0020: derandomized, no deadline, bounded examples (the same profile as fransys-model).
settings.register_profile("fransys", deadline=None, derandomize=True, max_examples=25)
settings.load_profile("fransys")


@record(kind="thing")
class Thing:
    """Toy table record: something with a name."""

    id: Id[Thing]
    key: AuthoringKey
    name: str
    ext: frozendict[str, Value] = frozendict()


@record(kind="link")
class Link:
    """Toy table record: a reference from one `Thing` to another."""

    id: Id[Link]
    key: AuthoringKey
    a: Id[Thing]
    b: Id[Thing]
    ext: frozendict[str, Value] = frozendict()


@value
class Label:
    """Toy value record: a nested value with no identity of its own."""

    text: str


@pytest.fixture
def thing_cls() -> type[Thing]:
    """The toy `Thing` record kind."""
    return Thing


@pytest.fixture
def link_cls() -> type[Link]:
    """The toy `Link` record kind: two `Id[Thing]` references."""
    return Link


@pytest.fixture
def origin() -> Origin:
    """A stable `Origin` for tests that don't care which line authored a record."""
    return Origin(file="conftest.py", line=1, note="fixture")


@pytest.fixture
def model_of() -> Callable[..., Model]:
    """Build a `Model` directly, `freeze()` not existing yet: `model_of((record, origin), ...)`."""

    def build(*entries: tuple[Record, Origin]) -> Model:
        tables: dict[str, dict[Id[Any], Record]] = {}
        for entry, _ in entries:
            tables.setdefault(entry.id.kind, {})[entry.id] = entry
        return Model(
            schema_version=1,
            tables=frozendict({kind: frozendict(rows) for kind, rows in tables.items()}),
            aliases=frozendict(),
            origins=frozendict({entry.id: origin for entry, origin in entries}),
            hashes=frozendict(),
            digests=frozendict(),
            digest="",
        )

    return build


@pytest.fixture(autouse=True)
def _restore_kind_registry() -> Iterator[None]:
    """Give each test the kind registry it found, so the suite can run twice in one process.

    Tests register throwaway kinds and assert on the exact name; restored in place, so a module
    that bound `registry._kinds` by name still sees the live dict.
    """
    kinds = dict(registry._kinds)
    by_name = {name: list(classes) for name, classes in registry._records_by_name.items()}
    values = set(registry._value_classes)
    yield
    registry._kinds.clear()
    registry._kinds.update(kinds)
    registry._records_by_name.clear()
    registry._records_by_name.update(by_name)
    registry._value_classes.clear()
    registry._value_classes.update(values)
