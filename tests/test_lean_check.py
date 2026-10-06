"""`scripts/lean_check.py`: the ceilings merge, the layout directory exemption, robustness.

Loaded like `test_lean_ceilings.py` loads `scripts/lean_ceilings.py` (`importlib.util.spec_from_
file_location`), since the script is not a package module. `test_layout_directory_exempt_*`
below are the two real-repo probes this order's own text names explicitly; every other case
builds its own small `CeilingsFile`/measured dict by hand.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, relpath: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relpath)
    if spec is None or spec.loader is None:
        msg = f"could not load {relpath}"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


lean_check = _load("fransys_lean_check", "scripts/lean_check.py")
lean_ceilings = lean_check.lean_ceilings


# --- Part A: build_ceilings, the merge (never a rewrite) -----------------------------------


def test_build_ceilings_from_scratch_uses_the_hand_authored_starting_values():
    """`existing=None` writes `STARTING_LIMITS`/`STARTING_EXEMPT` verbatim, sections via
    `first_run`.
    """
    measured = {"statements": {"pkg/a.py::f": 20}, "nested_defs": {"pkg/b.py::g": 2}}
    file = lean_check.build_ceilings(None, measured)

    assert file.limits == lean_check.STARTING_LIMITS
    assert file.exempt == lean_check.STARTING_EXEMPT
    assert file.sections == measured


def test_build_ceilings_merge_never_touches_limits_or_exempt():
    """A hand-authored `[limits]`/`[exempt]` survives a merge untouched; only sections change."""
    existing = lean_ceilings.CeilingsFile(
        limits={"statements": 15},
        sections={"statements": {"pkg/old.py::f": 999}},
        exempt={"pkg/custom.py::g": "hand-added (test-0001)"},
    )
    measured = {"statements": {"pkg/a.py::f": 30}}

    merged = lean_check.build_ceilings(existing, measured)

    assert merged.limits == {"statements": 15}
    assert merged.exempt == {"pkg/custom.py::g": "hand-added (test-0001)"}
    assert merged.sections == {"statements": {"pkg/a.py::f": 30}}
    assert "pkg/old.py::f" not in merged.sections["statements"]


def test_build_ceilings_merge_is_idempotent_and_preserves_hand_added_exempt():
    """Running the merge twice back-to-back on the same `measured` renders byte-identical text,
    and a hand-added `[exempt]` entry survives the second merge unchanged (Part A's own
    "merge, never a rewrite" design, proven).
    """
    existing = lean_ceilings.CeilingsFile(
        limits={"statements": 15},
        sections={},
        exempt={"pkg/custom.py::g": "hand-added (test-0001)"},
    )
    measured = {"statements": {"pkg/a.py::f": 30}}

    once = lean_check.build_ceilings(existing, measured)
    twice = lean_check.build_ceilings(once, measured)

    assert once.exempt == twice.exempt == {"pkg/custom.py::g": "hand-added (test-0001)"}
    assert once.limits == twice.limits == {"statements": 15}
    assert lean_ceilings.render_ceilings(once) == lean_ceilings.render_ceilings(twice)


def test_build_ceilings_exempt_site_never_appears_in_a_fresh_baseline():
    """A site named in `STARTING_EXEMPT` never gets a ceilings entry from `first_run`."""
    exempt_site = next(iter(lean_check.STARTING_EXEMPT))
    measured = {"module_code_lines": {exempt_site: 999, "pkg/other.py": 310}}

    file = lean_check.build_ceilings(None, measured)

    assert exempt_site not in file.sections["module_code_lines"]
    assert file.sections["module_code_lines"] == {"pkg/other.py": 310}


# --- the layout directory exemption: real repo, the two probes this order's text names -----


def test_directory_exempt_covers_an_unreasoned_site_under_it(tmp_path: Path) -> None:
    """A directory-scope `[exempt]` key, matched via `is_exempt_under`, hides every bare
    `noqa` under it; the same site is reported without the key.
    """
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "mod.py").write_text("x = 1  # noqa: E501\n", encoding="utf-8")
    sites = lean_check.lean_code_gates.unreasoned_sites([tmp_path / "pkg"], tmp_path)

    assert len(sites) == 1
    assert lean_check.lean_code_gates.report_unreasoned(sites, {"pkg": "why"}) == ()


def test_layout_has_no_unreasoned_suppression_even_without_the_exempt_entry():
    """LG1 backfill: every layout `noqa`/`ty: ignore` carries a reason, with no `[exempt]` help."""
    layout = ROOT / "packages/fransys-layout"
    sites = lean_check.lean_code_gates.unreasoned_sites([layout / "src", layout / "tests"], ROOT)

    assert sites == ()


def test_directory_exempt_does_not_skip_an_exact_numeric_site():
    """The same directory-scoped exempt entry never matches `lean_ceilings.check`'s own
    exact-match numeric sites, even one that sits under the exempt directory.
    """
    exempt = {"packages/pkg": "why"}
    site = "packages/pkg/src/pkg/mod.py::discover_chains"

    violations = lean_ceilings.check({site: 20}, ceilings={}, limit=15, exempt=exempt)

    assert violations == (lean_ceilings.Violation(site=site, measured=20, limit=15, listed=False),)


# --- the D8 module_code_lines exemption, real repo ------------------------------------------


def test_module_code_lines_first_run_excludes_the_d8_exempt_files():
    """Both D8-exempt files never appear in a fresh `[module_code_lines]` baseline.

    `types.py` is over 300 code lines today (real measurement); `text_metrics.py` is not, so
    its own exclusion is proven with a fabricated over-limit entry instead -- either way, an
    `[exempt]` site never gets a ceilings entry from `first_run`.
    """
    measured = lean_check.lean_code_shape.measure_module_code_lines(ROOT, limit=300)
    types_py = "packages/fransys-layout/src/fransys_layout/stages/types.py"
    text_metrics_py = "packages/fransys-layout/src/fransys_layout/geometry/text_metrics.py"
    assert types_py in measured
    assert text_metrics_py not in measured
    measured = {**measured, text_metrics_py: 999}

    file = lean_check.build_ceilings(None, {"module_code_lines": measured})

    assert types_py not in file.sections["module_code_lines"]
    assert text_metrics_py not in file.sections["module_code_lines"]


# --- robustness: a raising checker never partially writes ----------------------------------


def _write_ceilings_text(path: Path) -> str:
    text = (
        "[limits]\n"
        "statements = 15\n"
        "complexity = 8\n"
        "branches = 12\n"
        "module_code_lines = 300\n"
        "docstring_lines = 5\n"
        "surface_docstring_lines = 15\n"
        "md_tokens = 5000\n"
        "sentence_words = 30\n"
        "\n"
        "[nested_defs]\n"
        '"some/site.py::f" = 5\n'
    )
    path.write_text(text, encoding="utf-8")
    return text


def test_a_raising_checker_aborts_lower_without_deleting_anything(tmp_path, monkeypatch):
    """`lower`'s CLI entry point catches a checker's own exception, writes NOTHING, exits
    non-zero -- it never silently continues with a partial/empty measured dict for that section.
    """
    ceilings_path = tmp_path / "ceilings.toml"
    before = _write_ceilings_text(ceilings_path)

    def _boom(_root):
        msg = "stubbed checker failure"
        raise RuntimeError(msg)

    monkeypatch.setattr(lean_check.lean_code_shape, "measure_nested_defs", _boom)
    monkeypatch.setattr(lean_check, "CEILINGS_PATH", ceilings_path)

    exit_code = lean_check.main(["lower"])

    assert exit_code == 1
    assert ceilings_path.read_text(encoding="utf-8") == before


def test_a_raising_checker_aborts_first_run_without_writing_anything(tmp_path, monkeypatch):
    """Same abort contract for `first-run`, against a `ceilings.toml` that does not exist yet."""
    ceilings_path = tmp_path / "ceilings.toml"

    def _boom(_root):
        msg = "stubbed checker failure"
        raise RuntimeError(msg)

    monkeypatch.setattr(lean_check.lean_code_shape, "measure_nested_defs", _boom)
    monkeypatch.setattr(lean_check, "CEILINGS_PATH", ceilings_path)

    exit_code = lean_check.main(["first-run"])

    assert exit_code == 1
    assert not ceilings_path.exists()


def test_a_bad_ruff_exit_code_raises_instead_of_returning_empty_sections(monkeypatch):
    """`measure_ruff_sections` raises on an unexpected ruff exit code (a crash, exit 2) rather
    than silently returning three empty sections that `lower` would then read as "all clear".
    """

    class _FakeCompleted:
        returncode = 2
        stdout = ""
        stderr = "ruff: invalid --config"

    monkeypatch.setattr(
        lean_check.lean_code_gates.subprocess, "run", lambda *_args, **_kwargs: _FakeCompleted()
    )

    with pytest.raises(RuntimeError, match="exited 2"):
        lean_check.lean_code_gates.measure_ruff_sections(ROOT)


# --- limits/checker drift guard --------------------------------------------------------------


def test_assert_limits_match_checkers_passes_for_the_real_starting_limits():
    """The hand-authored `STARTING_LIMITS` agree with every checker's own hardcoded default."""
    lean_check._assert_limits_match_checkers(lean_check.STARTING_LIMITS)


def test_assert_limits_match_checkers_rejects_drift():
    """A `[limits]` value that disagrees with a checker's own constant raises, loudly."""
    drifted = dict(lean_check.STARTING_LIMITS)
    drifted["statements"] = 999
    with pytest.raises(ValueError, match="statements"):
        lean_check._assert_limits_match_checkers(drifted)


# --- enforce: numeric_violations over the real measurers' output, cmd_enforce's exit/text ----


def _module(root: Path, relpath: str, text: str) -> str:
    path = root / "packages" / "p" / "src" / "p" / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path.relative_to(root).as_posix()


def _fn_with(statements: int) -> str:
    body = "".join(f"    x{i} = {i}\n" for i in range(statements))
    return f"def f():\n{body}"


def _numeric(root: Path, keys: dict[str, dict[str, int]] | None = None):
    sections = {
        **lean_check.lean_code_gates.measure_ruff_sections(root),
        "nested_defs": lean_check.lean_code_shape.measure_nested_defs(root),
        "module_code_lines": lean_check.lean_code_shape.measure_module_code_lines(root, limit=300),
    }
    file = lean_ceilings.CeilingsFile(
        limits=dict(lean_check.STARTING_LIMITS), sections=keys or {}, exempt={}
    )
    return lean_check.numeric_violations(sections, file)


def test_enforce_statements_unlisted_listed_and_grown(tmp_path: Path):
    """16 statements without a key fail; keyed at 16 passes; grown to 17 fails as listed."""
    site = _module(tmp_path, "m.py", _fn_with(16)) + "::f"
    unkeyed = _numeric(tmp_path)
    assert [(s, v.site, v.measured, v.limit, v.listed) for s, v in unkeyed] == [
        ("statements", site, 16, 15, False)
    ]

    assert _numeric(tmp_path, {"statements": {site: 16}}) == []

    _module(tmp_path, "m.py", _fn_with(17))
    grown = _numeric(tmp_path, {"statements": {site: 16}})
    assert [(s, v.site, v.measured, v.limit, v.listed) for s, v in grown] == [
        ("statements", site, 17, 16, True)
    ]


def test_enforce_nested_def_fails_but_lambda_does_not(tmp_path: Path):
    """A nested `def` is a nested_defs violation; a lambda in the same shape is not."""
    site = _module(tmp_path, "m.py", "def f():\n    def g():\n        return 1\n    return g\n")
    got = _numeric(tmp_path)
    assert [(s, v.site) for s, v in got] == [("nested_defs", site + "::f")]

    _module(tmp_path, "m.py", "def f():\n    g = lambda: 1\n    return g\n")
    assert _numeric(tmp_path) == []


def test_enforce_module_code_lines_301_fails_300_passes(tmp_path: Path):
    """A module of 301 code lines is over the 300 limit; one of 300 is not."""
    site = _module(tmp_path, "big.py", "".join(f"a{i} = {i}\n" for i in range(301)))
    got = _numeric(tmp_path)
    assert [(s, v.site, v.measured, v.limit, v.listed) for s, v in got] == [
        ("module_code_lines", site, 301, 300, False)
    ]

    _module(tmp_path, "big.py", "".join(f"a{i} = {i}\n" for i in range(300)))
    assert _numeric(tmp_path) == []


def test_enforce_moved_function_is_flagged_at_its_new_path(tmp_path: Path):
    """A 16-statement function moved to a new module, key left on the old path, fails there."""
    old = "packages/p/src/p/old.py::f"
    new = _module(tmp_path, "new.py", _fn_with(16)) + "::f"

    got = _numeric(tmp_path, {"statements": {old: 16}})

    assert [(s, v.site, v.listed) for s, v in got] == [("statements", new, False)]


def test_cmd_enforce_exit_code_and_text(tmp_path: Path, monkeypatch, capsys):
    """Exit 1 and one line naming section, site and both numbers for a grown site; exit 0 clean."""
    ceilings_path = tmp_path / "ceilings.toml"
    ceilings_path.write_text(
        lean_ceilings.render_ceilings(
            lean_ceilings.CeilingsFile(
                limits=dict(lean_check.STARTING_LIMITS),
                sections={"statements": {"a.py::f": 16}},
                exempt={},
            )
        ),
        encoding="utf-8",
    )
    measured = {"statements": {"a.py::f": 17, "b.py::g": 20}}
    monkeypatch.setattr(
        lean_check,
        "measure_all",
        lambda _root, _limits: types.SimpleNamespace(sections=measured),
    )

    assert lean_check.cmd_enforce(tmp_path, ceilings_path) == 1
    out = capsys.readouterr().out.splitlines()
    assert out == [
        "enforce: [statements] a.py::f: measured 17 > ceiling 16 (listed, grown past its ceiling)",
        "enforce: [statements] b.py::g: measured 20 > limit 15 (unlisted, no ceilings.toml key)",
    ]

    measured["statements"] = {"a.py::f": 16}
    assert lean_check.cmd_enforce(tmp_path, ceilings_path) == 0
    assert capsys.readouterr().out == ""


# --- lower: what a deleted key says (gone vs within limit), and lower never raises a value ----


def _lower(tmp_path: Path, monkeypatch, capsys, ceilings: dict, measured: dict):
    """Run `cmd_lower` on `tmp_path` with `measure_all` stubbed; return (exit, lines, file text)."""
    path = tmp_path / "ceilings.toml"
    path.write_text(
        lean_ceilings.render_ceilings(
            lean_ceilings.CeilingsFile(
                limits=dict(lean_check.STARTING_LIMITS), sections=ceilings, exempt={}
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(lean_check, "cmd_hard", lambda _root, _path: 0)
    monkeypatch.setattr(
        lean_check, "measure_all", lambda _root, _limits: types.SimpleNamespace(sections=measured)
    )
    code = lean_check.cmd_lower(tmp_path, path)
    return code, capsys.readouterr().out.splitlines(), path.read_text(encoding="utf-8")


def test_lower_deleted_key_whose_file_is_gone_says_gone(tmp_path, monkeypatch, capsys):
    """A key whose file no longer exists prints `(gone)`, not `(within limit)`."""
    key = "packages/p/src/p/old.py::f"
    code, lines, _ = _lower(tmp_path, monkeypatch, capsys, {"statements": {key: 16}}, {})
    assert code == 0
    assert lines == [f"lowered [statements]: {key} deleted (gone)"]


def test_lower_deleted_key_whose_function_is_now_short_says_within_limit(
    tmp_path, monkeypatch, capsys
):
    """A method that still exists (dotted qualname) and is now short says `(within limit)`."""
    rel = _module(tmp_path, "m.py", "class _Plant:\n    def __init__(self):\n        pass\n")
    key = f"{rel}::_Plant.__init__"
    _, lines, _ = _lower(tmp_path, monkeypatch, capsys, {"statements": {key: 16}}, {})
    assert lines == [f"lowered [statements]: {key} deleted (within limit)"]


def test_lower_deleted_key_whose_function_left_an_existing_file_says_gone(
    tmp_path, monkeypatch, capsys
):
    """The file exists but the function is not in it: `(gone)`; a file check alone is not enough."""
    rel = _module(tmp_path, "m.py", "def other():\n    pass\n")
    key = f"{rel}::f"
    _, lines, _ = _lower(tmp_path, monkeypatch, capsys, {"statements": {key: 16}}, {})
    assert lines == [f"lowered [statements]: {key} deleted (gone)"]


def test_lower_gone_function_names_the_new_path_where_it_is_over_its_limit(
    tmp_path, monkeypatch, capsys
):
    """A moved function: `(gone)` plus every other path with the same qualname, sorted."""
    old = "packages/p/src/p/old.py::f"
    new_b = _module(tmp_path, "b.py", _fn_with(16))
    new_a = _module(tmp_path, "a.py", _fn_with(16))
    measured = {"statements": {f"{new_b}::f": 16, f"{new_a}::f": 16, f"{new_a}::g": 16}}
    _, lines, _ = _lower(tmp_path, monkeypatch, capsys, {"statements": {old: 16}}, measured)
    note = f"(gone) -- same name now over its limit at {new_a}, {new_b}"
    assert lines == [f"lowered [statements]: {old} deleted {note}"]


def test_lower_never_raises_a_value_and_enforce_still_fails(tmp_path, monkeypatch, capsys):
    """A site grown above its ceiling leaves the file byte-identical; `enforce` still fails."""
    ceilings = {"statements": {"a.py::f": 16}}
    measured = {"statements": {"a.py::f": 17}}
    code, lines, after = _lower(tmp_path, monkeypatch, capsys, ceilings, measured)
    path = tmp_path / "ceilings.toml"
    before = lean_ceilings.render_ceilings(
        lean_ceilings.CeilingsFile(
            limits=dict(lean_check.STARTING_LIMITS), sections=ceilings, exempt={}
        )
    )
    assert (code, lines, after) == (0, ["no ceiling lowered"], before)
    assert lean_check.cmd_enforce(tmp_path, path) == 1


def test_lower_lowers_a_shrunk_site(tmp_path, monkeypatch, capsys):
    """A site measured below its ceiling is lowered in the file and reported."""
    ceilings = {"statements": {"a.py::f": 20}}
    _, lines, after = _lower(
        tmp_path, monkeypatch, capsys, ceilings, {"statements": {"a.py::f": 18}}
    )
    assert lines == ["lowered [statements]: a.py::f 20 -> 18"]
    assert lean_ceilings.load_ceilings(tmp_path / "ceilings.toml").sections == {
        "statements": {"a.py::f": 18}
    }
    assert '"a.py::f" = 18' in after


# --- Part C: surface docstring length goes through enforce and first-run ---------------------


def _surface_fn(tmp_path: Path, extra_lines: int) -> tuple[object, str]:
    """A tmp surface function `f` whose docstring has `extra_lines` body lines; (entry, site)."""
    body = "\n".join(f"    Line {n}." for n in range(extra_lines))
    path = tmp_path / "surf.py"
    path.write_text(
        f'def f():\n    """Summary.\n\n{body}\n    """\n    return 1\n', encoding="utf-8"
    )
    entry = lean_check.lean_surface.SurfaceName(
        module="fake", name="f", defining_file=path, qualname="f"
    )
    return entry, "surf.py::f"


def _measured_surface(tmp_path: Path, extra_lines: int) -> dict[str, dict[str, int]]:
    entry, _ = _surface_fn(tmp_path, extra_lines)
    return {
        "surface_docstring_lines": lean_check.lean_docstrings.measure_surface_docstring_lines(
            limit=15, entries=(entry,), root=tmp_path
        )
    }


def test_surface_docstring_of_16_lines_without_a_ceiling_fails_enforce(tmp_path):
    """A 16-line surface docstring is unlisted over 15 and fails; a 15-line one passes."""
    empty = lean_ceilings.CeilingsFile(
        limits=dict(lean_check.STARTING_LIMITS), sections={}, exempt={}
    )
    found = lean_check.numeric_violations(_measured_surface(tmp_path, 13), empty)
    assert [(s, v.site, v.measured, v.limit, v.listed) for s, v in found] == [
        ("surface_docstring_lines", "surf.py::f", 16, 15, False)
    ]
    assert lean_check.numeric_violations(_measured_surface(tmp_path, 12), empty) == []


def test_first_run_writes_a_ceiling_for_an_over_limit_surface_docstring(tmp_path):
    """`first-run`'s merge keys the 16-line docstring at 16; with that key enforce passes, and
    one more docstring line fails again.
    """
    measured = _measured_surface(tmp_path, 13)
    file = lean_check.build_ceilings(None, measured)
    assert file.sections["surface_docstring_lines"] == {"surf.py::f": 16}
    assert lean_check.numeric_violations(measured, file) == []
    grown = _measured_surface(tmp_path, 14)
    assert [v.site for _, v in lean_check.numeric_violations(grown, file)] == ["surf.py::f"]


# --- ceilings.toml notes: the renderer owns them ----------------------------------------------

_DOCSTRING_NOTE = "docstring_lines = 5  # summary, blank, two why lines, closing quotes (LC3)"


def test_committed_ceilings_round_trip_byte_for_byte():
    """Rendering the parsed committed file gives it back; a hand comment cannot survive."""
    path = ROOT / "ceilings.toml"
    text = path.read_text(encoding="utf-8")
    rendered = lean_check._HEADER + lean_ceilings.render_ceilings(lean_ceilings.load_ceilings(path))
    assert rendered == text, "keep the tool's order, put any note in the renderer"


def test_lower_write_path_keeps_the_docstring_lines_note(tmp_path, monkeypatch, capsys):
    """`cmd_lower` lowering one ceiling still writes the `docstring_lines` note."""
    ceilings = {"statements": {"a.py::f": 20}}
    limits = {**lean_check.STARTING_LIMITS, "docstring_lines": 5}
    monkeypatch.setattr(lean_check, "STARTING_LIMITS", limits)
    _, _, after = _lower(tmp_path, monkeypatch, capsys, ceilings, {"statements": {"a.py::f": 18}})
    assert _DOCSTRING_NOTE in after.splitlines()
    assert '"a.py::f" = 18' in after
