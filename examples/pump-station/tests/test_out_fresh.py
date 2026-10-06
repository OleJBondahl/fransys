"""`out/` freshness check (spec E9): the committed exports equal a fresh build, byte for byte.

Its own module, not folded into another test file: it runs the full build (slow-ish), which
`test_smoke.py` and the other STEP 4 test modules don't need. The can-fail proof for this test
(spec step 4: flip a byte in a committed export, confirm this test fails, revert) is a manual
verification done once with `Edit`, not a permanent test -- see the STEP 4 report.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
COMMITTED_OUT_DIR = REPO_ROOT / "out"


def test_committed_out_dir_matches_a_fresh_build(built: tuple) -> None:
    _result, fresh_out_dir, _intermediates = built

    committed_files = {
        p.relative_to(COMMITTED_OUT_DIR) for p in COMMITTED_OUT_DIR.rglob("*") if p.is_file()
    }
    fresh_files = {p.relative_to(fresh_out_dir) for p in fresh_out_dir.rglob("*") if p.is_file()}
    assert committed_files, "expected out/ to hold at least one committed file"
    assert fresh_files, "expected the fresh build to write at least one file"
    assert committed_files == fresh_files, (
        f"file sets differ; only in committed: {committed_files - fresh_files}; "
        f"only in fresh build: {fresh_files - committed_files}"
    )

    for rel_path in sorted(committed_files):
        committed_bytes = (COMMITTED_OUT_DIR / rel_path).read_bytes()
        fresh_bytes = (fresh_out_dir / rel_path).read_bytes()
        assert committed_bytes == fresh_bytes, f"{rel_path} differs from a fresh build"
