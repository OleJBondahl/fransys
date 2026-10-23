"""Shared synthetic fixtures. Built only from examples/demo-parts.

Each fixture authors through `fransys_author`, then merges, freezes, numbers, allocates
PLC and lays out through `fr.build(...)`: the facade's acceptance, the
proof that `build` is the real pipeline. Root tests may import every workspace package.
"""

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import fransys as fr
import fransys_author
import fransys_parts
import pytest

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    # `--import-mode=importlib` (root pyproject.toml) never puts the rootdir on `sys.path`,
    # and `demo_designs` is a plain script module, not an installed package (unlike
    # `fransys_parts` and friends above), so it needs this the way
    # `tests/test_reauthoring.py` needs it for `layout_cabinet`.
    sys.path.insert(0, str(_ROOT))

_TESTS = str(_ROOT / "tests")  # the tests import their sibling test modules by name
if _TESTS not in sys.path:
    sys.path.insert(0, _TESTS)

from _export_signature import SKIP_REASON, is_export  # noqa: E402
from _model_build_cover import cabinet_document  # noqa: E402
from demo_designs import cabinet_design, harness_with_board_design  # noqa: E402

if TYPE_CHECKING:
    from fransys.pipeline import BuildResult
    from fransys_author import Design

    from fransys_model.kernel import Draft, Model

DEMO_PARTS = _ROOT / "examples" / "demo-parts"


def _built(parts: Draft, design: Design) -> BuildResult:
    """`fr.build(parts, design.draft(), <a SYSTEM document>)`: its result, the model laid out.

    Merges, freezes, numbers, allocates PLC and lays out. Structural problems (an unfrozen
    model, a `LayoutError`) raise; every pass's
    `Finding`s are just not asserted on here -- the fixture only needs to reach a laid
    out model, not a finding-free one. The `SYSTEM` document (no subject) is here only to
    satisfy PS1's "layout runs only on a model with a document" gate (MODEL-BUILD, decision
    0037): it changes no layout record and no CSV/XML/HTML export byte (verified empirically,
    `_model_build_cover.py`'s own docstring), so this keeps this fixture's own documented
    contract -- "the two root fixtures build a laid-out model", `tests/test_fixtures.py` --
    true again, unchanged from before PS1.
    """
    document = cabinet_document(fransys_author.Design(parts).location("C1", "Demo cabinet"))
    return fr.build(parts, design.draft(), document)


@pytest.fixture
def demo_cabinet_result() -> BuildResult:
    """A small cabinet: supply, one relay circuit, a terminal strip, one field cable."""
    parts = fransys_parts.load("demo_parts")
    return _built(parts, cabinet_design(parts))


@pytest.fixture
def demo_cabinet(demo_cabinet_result: BuildResult) -> Model:
    """`demo_cabinet_result`'s model."""
    return demo_cabinet_result.model


@pytest.fixture
def demo_harness_with_board_result() -> BuildResult:
    """A harness mated to a board that carries a relay and two connectors."""
    parts = fransys_parts.load("demo_parts")
    return _built(parts, harness_with_board_design(parts))


@pytest.fixture
def demo_harness_with_board(demo_harness_with_board_result: BuildResult) -> Model:
    """`demo_harness_with_board_result`'s model."""
    return demo_harness_with_board_result.model


@pytest.fixture
def demo_cabinet_document(tmp_path: Path) -> BuildResult:
    """The demo cabinet as a `CABINET_SCHEMATIC` document, with its default pages (F9, P13).

    `SCHEMATIC` is kept: `fransys_render.pages`/`check` are fully implemented now, so the
    document's real laid-out schematic pages render and export cleanly, with no
    `DOCUMENT_NO_DRAWINGS` finding. Returns the `BuildResult`, not collapsed to `.model` like
    `_built`'s fixtures -- this fixture exists to exercise `fr.write`, which needs the findings
    alongside the model. Cover and notes text are written fresh under `tmp_path` each call
    (function-scoped, matching `demo_cabinet`), never a tracked example asset.
    """
    parts = fransys_parts.load("demo_parts")
    design = cabinet_design(parts)
    # `Design(parts).location("C1", ...)` mints the same id `cabinet_design` already put in
    # its own draft (a location's id is a deterministic hash of its key); this scratch
    # `Design`'s own draft is discarded -- only the returned handle's id is used.
    c1 = fransys_author.Design(parts).location("C1", "Demo cabinet")
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Demo cabinet\n", encoding="utf-8")
    (tmp_path / "cabinet.notes.md").write_text(
        "Invented demo notes for the cabinet.\n", encoding="utf-8"
    )
    document_draft = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, c1, cover=cover)
    return fr.build(parts, design.draft(), document_draft)


pytest_plugins = (
    "_gap_flip_hook",
)  # the strict xfails of the tests still red on the core (FLIP-NOW F4)

HEAVY_MODULES = ("test_scale_call_counts.py", "test_render_scale_counts.py")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Put each scale-count module at the start of its own xdist worker slice (AW15).

    Each module holds a worker for a `build_scale(16)`. xdist gives worker k the k-th slice of
    `len(items) // workers` tests and runs it in order. Order only; the rest keep theirs.
    In the export (no `internal/` root) a `private_input` test is skipped (R462).
    """
    workers = getattr(config, "workerinput", {}).get("workercount", 1)
    names = [Path(str(item.path)).name for item in items]
    groups = [[i for i, n in zip(items, names, strict=True) if n == m] for m in HEAVY_MODULES]
    rest = [i for i, n in zip(items, names, strict=True) if n not in HEAVY_MODULES]
    step = len(items) // workers if workers > 1 else 0
    for k in range(len(groups)):
        rest[k * step : k * step] = groups[k]
    items[:] = rest
    if is_export():
        skip = pytest.mark.skip(reason=SKIP_REASON)
        for item in items:
            if item.get_closest_marker("private_input"):
                item.add_marker(skip)
