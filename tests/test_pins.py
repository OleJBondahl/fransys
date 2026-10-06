"""Exact-pin gate: every dependency in the workspace is a bare `==` pin, or a PEP 508 direct
reference pinned to an exact tag, `@vX.Y.Z` (root `CLAUDE.md` red flags, `docs/DESIGN.md`: "a
floating version range is never allowed"; decision 0014, amended by 0017 for the release recipe's
direct references).

Parses every `pyproject.toml` in the workspace: the root one, plus every directory root
`[tool.uv.workspace].members` resolves to -- not a `packages/*` glob, so a member declared outside
`packages/` (`examples/demo-parts`, or any future top-level group) is walked too. Walks the three
tables a dependency can live in: `[project] dependencies`, `[project.optional-dependencies]`
(every group) and `[dependency-groups]` (every group; this is where the root's dev tools live).
See `docs/decisions/0014-*.md` for what counts as a violation, the workspace-member exemption, and
what this deliberately does not check, and `docs/decisions/0017-*.md` for the direct-reference
shape a release commit writes.
"""

import re
import tomllib
from pathlib import Path

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
ROOT_PYPROJECT = WORKSPACE_ROOT / "pyproject.toml"

# Any of these appearing in the version part of a requirement (after stripping the marker) is a
# range, caret, tilde, not-equal or wildcard operator -- never an exact pin.
_RANGE_CHARS = frozenset("<>~^!*")

# `name`, optional `[extras]`, then whatever specifier text remains (may be empty: a bare name).
_REQUIREMENT = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(\[[^\]]*\])?\s*(.*)$")

# A PEP 508 direct reference (`name @ url`) pinned to an exact tag: `git+https://`, a host and
# path with no `@` or `#` of its own, then `@vX.Y.Z` -- integers only, nothing after the third
# number but an optional `#subdirectory=...` fragment. `fullmatch` (not `search` with a `$`
# anchor) so nothing can smuggle an untagged prefix or a suffixed tag past the check: `search`
# with only a trailing `$` still accepts `...@main#subdirectory=z@v0.1.0` because the match can
# start anywhere in the string, and a `$`-only anchor with no `fullmatch` lets `@v0.1.0-rc1` match
# on the `@v0.1.0` prefix and ignore the `-rc1` suffix instead of failing on it.
_DIRECT_REFERENCE = re.compile(r"git\+https://[^\s@#]+@v\d+\.\d+\.\d+(?:#subdirectory=[^\s@#]+)?")


def _normalize(name: str) -> str:
    """PEP 503 normalisation: `-`, `_` and `.` are the same separator, case-insensitive."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _load(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _resolve_workspace_members(root: dict) -> list[Path]:
    """Directories `[tool.uv.workspace].members` resolves to, the way `uv` itself resolves them:
    each entry is a literal path or a glob pattern, matched against directories that hold a
    `pyproject.toml`; anything `[tool.uv.workspace].exclude` matches (the same table, when
    present) is dropped.

    This is the single source both file-discovery scope (`_pyproject_paths`) and the
    workspace-member exemption (`_workspace_member_names`) derive from, so the two cannot drift
    apart the way a hardcoded `packages/*` glob and this table did in the first draft of this
    gate -- that drift silently skipped `examples/demo-parts/pyproject.toml`, a real workspace
    member outside `packages/`.
    """
    workspace = root["tool"]["uv"]["workspace"]
    excluded: set[Path] = set()
    for pattern in workspace.get("exclude", []):
        excluded.update(WORKSPACE_ROOT.glob(pattern))
    resolved: list[Path] = []
    for pattern in workspace["members"]:
        is_glob = any(char in pattern for char in "*?[")
        matches = sorted(WORKSPACE_ROOT.glob(pattern)) if is_glob else [WORKSPACE_ROOT / pattern]
        resolved.extend(
            m
            for m in matches
            if m.is_dir() and (m / "pyproject.toml").is_file() and m not in excluded
        )
    return resolved


def _resolved_members() -> list[Path]:
    return _resolve_workspace_members(_load(ROOT_PYPROJECT))


def _workspace_member_names() -> frozenset[str]:
    """Package names that resolve through `[tool.uv.workspace]`/`[tool.uv.sources]`, not from an
    index -- so a bare workspace dependency (`"fransys-model"`, no version) is legitimate.

    Derived from the resolved member paths themselves, the same way `PURITY_SCOPE` in
    `tests/test_boundaries.py` derives its scope from a directory scan rather than a hardcoded
    list: each member path's own `pyproject.toml` supplies its real `[project.name]`, so a newly
    added workspace member is exempt automatically, with nothing here to update.
    """
    return frozenset(
        _normalize(_load(member / "pyproject.toml")["project"]["name"])
        for member in _resolved_members()
    )


def _dependency_specs(data: dict) -> list[tuple[str, str]]:
    """`(table, requirement)` pairs for every dependency `data` declares, across the three
    tables.
    """
    project = data.get("project", {})
    specs = [("project.dependencies", dep) for dep in project.get("dependencies", [])]
    for group, deps in project.get("optional-dependencies", {}).items():
        specs.extend((f"project.optional-dependencies.{group}", dep) for dep in deps)
    for group, deps in data.get("dependency-groups", {}).items():
        # A non-string entry is a PEP 735 `{include-group = "..."}` reference, not a dependency
        # pin; the group it points at is walked on its own turn.
        specs.extend((f"dependency-groups.{group}", dep) for dep in deps if isinstance(dep, str))
    return specs


def pin_violation(requirement: str, workspace_members: frozenset[str]) -> str | None:
    """Why `requirement` is not an exact pin, or `None` if it is (or an exempt bare workspace
    member, or a direct reference pinned to an exact tag).
    """
    without_marker = requirement.split(";", 1)[0].strip()
    match = _REQUIREMENT.match(without_marker)
    if match is None:
        return "unparsable requirement"
    name, specifier = match.group(1), match.group(3).strip()
    if not specifier:
        # A bare workspace member resolves through [tool.uv.sources]/[tool.uv.workspace], not
        # from an index -- exempt. A bare THIRD-PARTY name is still a violation: the exemption is
        # for the no-specifier case, never for the name, so a member written with a range (e.g.
        # "fransys-model>=0.0.0") still falls through to the checks below and fails.
        is_member = _normalize(name) in workspace_members
        return None if is_member else "bare dependency, no version specifier"
    if specifier.startswith("@"):
        # A PEP 508 direct reference: only a release commit writes these (decision 0017). A
        # branch, a bare commit sha, a short tag or a suffixed tag are all rejected; only an
        # exact `@vX.Y.Z` tag passes.
        url = specifier[1:].strip()
        is_exact_tag = _DIRECT_REFERENCE.fullmatch(url) is not None
        return None if is_exact_tag else "direct reference not pinned to an exact tag (@vX.Y.Z)"
    if "," in specifier:
        return "more than one specifier"
    if any(char in _RANGE_CHARS for char in specifier):
        return "range, caret, tilde or wildcard operator"
    return None if specifier.startswith("==") else "not an exact == pin"


def dependency_violations(data: dict, workspace_members: frozenset[str]) -> set[str]:
    found = set()
    for table, requirement in _dependency_specs(data):
        reason = pin_violation(requirement, workspace_members)
        if reason is not None:
            found.add(f"{table}: {requirement!r} ({reason})")
    return found


def _pyproject_paths() -> list[Path]:
    return [ROOT_PYPROJECT, *(member / "pyproject.toml" for member in _resolved_members())]


WORKSPACE_MEMBERS = _workspace_member_names()


@pytest.mark.parametrize(
    "pyproject_path", _pyproject_paths(), ids=lambda p: str(p.relative_to(WORKSPACE_ROOT))
)
def test_every_dependency_is_an_exact_pin(pyproject_path: Path):
    data = _load(pyproject_path)
    found = dependency_violations(data, WORKSPACE_MEMBERS)
    assert found == set()


def test_every_resolved_member_pyproject_is_walked():
    # Guards against re-hardcoding scope discovery (e.g. back to a `packages/*` glob), the same
    # way `test_boundaries.py`'s `test_every_source_package_is_in_the_table` guards its own
    # ALLOWED table against a directory scan drifting away from it: every directory
    # `[tool.uv.workspace].members` resolves to must have its `pyproject.toml` in the set this
    # gate actually parses, root included.
    resolved = {member / "pyproject.toml" for member in _resolved_members()}
    assert resolved <= set(_pyproject_paths())


def test_demo_parts_pyproject_is_in_scope():
    # Concrete regression proof for the hole this derivation replaced: examples/demo-parts is a
    # workspace member that lives outside packages/, so a packages/*-glob-based gate never read
    # it. It must appear in the parsed set on its own path, not folded into a generic assertion.
    assert WORKSPACE_ROOT / "examples" / "demo-parts" / "pyproject.toml" in _pyproject_paths()


def test_the_gate_can_fail():
    members = frozenset({"fransys-model"})
    range_reason = "range, caret, tilde or wildcard operator"
    # A range operator.
    assert pin_violation("hypothesis>=6.168.0", members) == range_reason
    # A bare dependency: the case a naive scan for range operators misses, since it has none.
    assert pin_violation("pytest-cov", members) == "bare dependency, no version specifier"
    # More than one specifier on one dependency.
    assert pin_violation("x==1.0,!=1.0", members) == "more than one specifier"
    # A caret or tilde, not just the four-character range operators.
    assert pin_violation("x~=1.0", members) == range_reason
    assert pin_violation("x==1.0.*", members) == range_reason
    # The workspace-member exemption is for the missing specifier, never for the name: a member
    # written with a range still fails.
    assert pin_violation("fransys-model>=0.0.0", members) == range_reason


def test_the_gate_accepts_only_a_direct_reference_pinned_to_an_exact_tag():
    members = frozenset()
    direct_reference_reason = "direct reference not pinned to an exact tag (@vX.Y.Z)"
    # A branch, not a tag.
    assert pin_violation("x @ git+https://example.com/x@main", members) == direct_reference_reason
    # A bare 40-character commit sha, not a tag.
    assert (
        pin_violation(f"x @ git+https://example.com/x@{'a' * 40}", members)
        == direct_reference_reason
    )
    # A short tag: missing the patch component.
    assert pin_violation("x @ git+https://example.com/x@v0.1", members) == direct_reference_reason
    # A tag with a suffix.
    assert (
        pin_violation("x @ git+https://example.com/x@v0.1.0-rc1", members)
        == direct_reference_reason
    )
    # A URL with no ref at all: no `@` after the host and path.
    assert pin_violation("x @ git+https://example.com/x", members) == direct_reference_reason
    # An exact tag passes, with or without a `#subdirectory=` fragment.
    assert pin_violation("x @ git+https://example.com/x@v0.1.0", members) is None
    assert (
        pin_violation("x @ git+https://example.com/x@v0.1.0#subdirectory=packages/x", members)
        is None
    )


def test_the_gate_does_not_fire_on_pins_markers_extras_or_workspace_members():
    members = frozenset({"fransys-model"})
    assert pin_violation("deal==4.24.6", members) is None
    assert pin_violation("x[extra]==1.0", members) is None
    assert pin_violation("x==1.0; python_version<'4'", members) is None
    # A bare workspace member is legitimate -- it resolves through [tool.uv.sources], not a pin.
    assert pin_violation("fransys-model", members) is None
    # Name normalisation: the workspace declares hyphens; an underscore or different case spelling
    # of the same package is still the same member.
    assert pin_violation("fransys_model", members) is None


def test_workspace_members_are_derived_not_hardcoded():
    # Every member comes from `[tool.uv.workspace].members`, resolved to directories and then
    # through each one's own `[project.name]` -- not a name list maintained here. Proof: every
    # name in this set actually is a resolved member's declared project name, and the set's size
    # matches the resolved member count (one name per member, no hardcoded extras or gaps).
    resolved = _resolved_members()
    assert len(WORKSPACE_MEMBERS) == len(resolved)
    assert "fransys-model" in WORKSPACE_MEMBERS
    assert "demo-parts" in WORKSPACE_MEMBERS  # examples/demo-parts, not under packages/


# `[tool.uv.sources]` is a second, separate hole from the one `pin_violation` closes above. A
# dependency can carry an exact `==0.1.0` requirement -- which the gate above is happy with --
# while `[tool.uv.sources]` quietly resolves that name from a moving branch instead of a tag: the
# version string gives false comfort while the actual content floats. So every root
# `[tool.uv.sources]` entry is checked on its own terms here: it must be a workspace member, or a
# git source pinned to an exact tag, or a git source pinned to a full 40-character commit hash --
# never a branch, never a bare git URL with no ref, never a path source.


def _root_sources() -> dict[str, dict]:
    """The root `[tool.uv.sources]` table, name -> source spec."""
    return _load(ROOT_PYPROJECT).get("tool", {}).get("uv", {}).get("sources", {})


_FULL_COMMIT_HASH = re.compile(r"[0-9a-fA-F]{40}")


def source_violation(source: dict) -> str | None:
    """Why a `[tool.uv.sources]` entry `source` is not a workspace member or an exact pin."""
    if source.get("workspace") is True:
        return None
    if "git" not in source:
        return (
            "path source"
            if "path" in source
            else "source is neither a workspace member nor a pinned git dependency"
        )
    if "tag" in source:
        return None
    rev = source.get("rev")
    if isinstance(rev, str) and _FULL_COMMIT_HASH.fullmatch(rev):
        return None
    if "branch" in source:
        return "git source pinned to a branch, not a tag or a full commit rev"
    return "git source with no exact tag or full 40-character commit rev"


@pytest.mark.parametrize("name", sorted(_root_sources()), ids=str)
def test_every_root_source_is_a_workspace_member_or_an_exact_pin(name: str):
    assert source_violation(_root_sources()[name]) is None


def test_root_sources_names_graphical_symbols():
    """A named expectation, not just a non-empty check: if `[tool.uv.sources]` were emptied or
    this entry renamed, the parametrized test above would collect zero cases and pass silently --
    the exact defect family (a smaller collected count, not a red test) this package exists to
    close.
    """
    assert "graphical-symbols" in _root_sources()


def test_the_source_gate_can_fail():
    assert (
        source_violation({"git": "https://example.com/x", "branch": "main"})
        == "git source pinned to a branch, not a tag or a full commit rev"
    )
    assert (
        source_violation({"git": "https://example.com/x"})
        == "git source with no exact tag or full 40-character commit rev"
    )
    assert source_violation({"path": "../local"}) == "path source"
    assert (
        source_violation({}) == "source is neither a workspace member nor a pinned git dependency"
    )


def test_the_source_gate_does_not_fire_on_workspace_members_tags_or_full_revs():
    assert source_violation({"workspace": True}) is None
    assert source_violation({"git": "https://example.com/x", "tag": "v0.1.0"}) is None
    assert source_violation({"git": "https://example.com/x", "rev": "a" * 40}) is None
