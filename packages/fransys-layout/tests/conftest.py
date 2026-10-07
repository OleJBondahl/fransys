import re
import sys
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

from fransys_model.kernel import Origin, evolve

if TYPE_CHECKING:
    from collections.abc import Callable

    from _typeshed import DataclassInstance

    from fransys_model.kernel import Model, Record

# --import-mode=importlib leaves the test directories off sys.path; the tests import their helpers
# by name: samples, layout_cabinet and debug_svg live here, coherence_helpers in lint and
# grid_path_oracle in stages. These three are appended, not inserted (workspace rule, see the
# model conftest).
for directory in (".", "lint", "stages"):
    sys.path.append(str(Path(__file__).parent / directory))


def pytest_addoption(parser: pytest.Parser) -> None:
    """`--regenerate-golden` rewrites the files of `tests/golden/` from the current engine.

    Run it by pointing pytest at this package, so that this conftest is loaded before the
    option is parsed: `uv run pytest packages/fransys-layout --regenerate-golden`. Then read
    `git diff tests/golden/` before committing: a golden is a claim about the layout.
    """
    parser.addoption(
        "--regenerate-golden",
        action="store_true",
        default=False,
        help="rewrite tests/golden/ from the current layout instead of comparing to it",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Refuse `--regenerate-golden` under pytest-xdist parallelism.

    Checked on the controller process, before workers spawn, so the run fails once with one
    clean message instead of once per worker: with `-n`, every worker process would otherwise
    overwrite the same golden files concurrently.
    """
    if config.getoption("--regenerate-golden") and config.getoption("numprocesses", None):
        message = (
            "--regenerate-golden must be run single-process (no -n): "
            "parallel workers would overwrite the golden files concurrently."
        )
        raise pytest.UsageError(message)


_VERSION_FIELDS = ("produced_by", "library_version")
_VERSION_TOKEN = re.compile(r" \d+\.\d+\.\d+")
_NORMALIZE_ORIGIN = Origin(file=__file__, line=1, note="golden version normalisation")


def _with_fixed_versions(model: Model) -> Model:
    """`model` with each version in `produced_by`/`library_version` replaced by "0.0.0".

    Names stay (decision layout-0119), so a renamed producer still moves a golden. Found from
    the records that carry either field; only changed records are removed and put back.
    """
    remove_ids = []
    put_records = []
    for table in model.tables.values():
        for record_id, record in table.items():
            changed = {
                field: _VERSION_TOKEN.sub(" 0.0.0", getattr(record, field))
                for field in _VERSION_FIELDS
                if hasattr(record, field)
            }
            if any(getattr(record, field) != value for field, value in changed.items()):
                remove_ids.append(record_id)
                put_records.append(
                    cast("Record", replace(cast("DataclassInstance", record), **changed))
                )
    if not put_records:
        return model
    return evolve(model, remove=remove_ids, put=put_records, origin=_NORMALIZE_ORIGIN)


@pytest.fixture
def normalized() -> Callable[[Model], Model]:
    """The one golden normaliser: every layout stamp keeps its names and gets version 0.0.0.

    A fixture, not an import: `--import-mode=importlib` keeps test directories off `sys.path`.
    Goldens are written through it and compared through it, so a version bump moves none.
    """
    return _with_fixed_versions
