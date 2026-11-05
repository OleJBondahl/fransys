import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """`--regenerate-golden` rewrites the files of `tests/golden/` from the current engine.

    Run it by pointing pytest at this package, so that this conftest is loaded before the
    option is parsed: `uv run pytest packages/fransys-layout --regenerate-golden`. Then read
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
    """
    if config.getoption("--regenerate-golden") and config.getoption("numprocesses", None):
        message = "--regenerate-golden must be run single-process (no -n): parallel workers would overwrite the golden files concurrently."
        raise pytest.UsageError(message)
