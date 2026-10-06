"""Determinism across processes: the same model gives the same bytes under any hash seed."""

import os
import subprocess
import sys
from pathlib import Path

_SCRIPT = Path(__file__).with_name("_write_fixture.py")


def _write_in_a_fresh_process(work: Path, hash_seed: str) -> tuple[str, dict[str, bytes]]:
    """Run the fixture script under `PYTHONHASHSEED=hash_seed`.

    Returns the hash the child computed for one fixed string, and each file it wrote by name.
    """
    done = subprocess.run(  # noqa: S603 -- our own interpreter and our own script
        [sys.executable, str(_SCRIPT), str(work)],
        env={**os.environ, "PYTHONHASHSEED": hash_seed},
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    files = {
        path.relative_to(work).as_posix(): path.read_bytes()
        for tree in ("out", "intermediates")
        for path in sorted((work / tree).rglob("*"))
        if path.is_file()
    }
    return (work / "hash-of-a-str.txt").read_text(encoding="utf-8"), files


def test_two_processes_with_different_hash_seeds_write_byte_equal_files(tmp_path):
    """Two harness documents written in two interpreters, seeds "1" and "2", differ in no byte.

    Root `CLAUDE.md` invariant 1: the same model digest always gives the same bytes.
    `test_two_writes_of_one_result_give_byte_equal_files` cannot see a set-order effect (one
    process has one hash seed) and its fixture has no `Document`, so no PDF is compared there.
    Here every file of `out_dir` and of the intermediates directory is compared: the PDFs, the
    `.typ` sources and the one remaining SVG. Both harness pages are cable tables now
    (CT1/CT2), no SVG of their own; `fransys_render.pages` still draws one `layout.page:...`
    SVG for the whole model regardless of either document's own `remove=(PageKind.SCHEMATIC,)`
    (`_draw_svgs`'s own docstring), so exactly one survives, not zero.

    The two children must really hold different hash seeds: each reports the hash of one fixed
    string, and the two values differ (a control, or equal bytes would prove nothing).
    """
    first_hash, first = _write_in_a_fresh_process(tmp_path / "seed1", "1")
    second_hash, second = _write_in_a_fresh_process(tmp_path / "seed2", "2")

    assert first_hash != second_hash
    names = sorted(first)
    assert names == sorted(second)
    # Not vacuous: the trees hold both PDFs, both Typst sources and one rendered SVG.
    suffixes = [name.rpartition(".")[2] for name in names]
    assert suffixes.count("pdf") == 2
    assert suffixes.count("typ") == 2
    assert suffixes.count("svg") == 1  # CT1: no dot spawn, no harness SVG any more
    assert all(first[name] for name in names)
    assert [name for name in names if first[name] != second[name]] == []
