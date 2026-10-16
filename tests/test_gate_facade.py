"""Facade gates E3 and E4 (spec SURFACE-COHERENCE R1): the findings policy and stored releases.

E3: outside `fransys`, no `BuildErrors` import and no compare or branch on `Severity.ERROR`,
bar `finding_errors`, the one home of the rule. A dict key is out of scope (designer 2026-10-16).
E4: the facade reads no `StoredRelease` field except through derive (the four-field rule is in
`test_one_home.py`).
"""

import ast
import dataclasses

from gate_scan import imports_of, src_imports, src_modules

from fransys_model.derive import baseline

FACADE = "fransys"
HOME = "fransys_model.derive.finding_errors"
STORED_FIELDS = frozenset(field.name for field in dataclasses.fields(baseline.StoredRelease))
STORED_RECEIVERS = frozenset(["release", "stored", "stored_release", "previous", "source"])


def _severity_names(tree: ast.AST) -> frozenset[str]:
    """`Severity` plus every alias it is imported under."""
    names = {"Severity"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names |= {a.asname for a in node.names if a.name == "Severity" and a.asname}
    return frozenset(names)


def _error_refs(node: ast.AST, names: frozenset[str]) -> list[ast.Attribute]:
    return [
        n
        for n in ast.walk(node)
        if isinstance(n, ast.Attribute)
        and n.attr == "ERROR"
        and isinstance(n.value, ast.Name)
        and n.value.id in names
    ]


def error_branches(source: str) -> list[int]:
    """E3: lines of `Severity.ERROR` in a compare, an if/while/comprehension test or a case."""
    tree = ast.parse(source)
    names = _severity_names(tree)
    scopes: list[ast.AST] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            scopes.append(node)
        elif isinstance(node, ast.If | ast.IfExp | ast.While):
            scopes.append(node.test)
        elif isinstance(node, ast.comprehension):
            scopes.extend(node.ifs)
        elif isinstance(node, ast.MatchValue):
            scopes.append(node.value)
    hits = {(ref.lineno, ref.col_offset) for scope in scopes for ref in _error_refs(scope, names)}
    return sorted(line for line, _ in hits)


def error_constructions(source: str) -> int:
    """The count of `Severity.ERROR` references in `source` (the non-hit positive control)."""
    tree = ast.parse(source)
    return len(_error_refs(tree, _severity_names(tree)))


def buildable_imports(source: str, module: str) -> list[int]:
    """E3: lines that import `BuildErrors` from anywhere, in `module`."""
    return [r.line for r in imports_of(source, module) if r.name == "BuildErrors"]


def stored_field_reads(source: str) -> list[tuple[str, int]]:
    """E4: `(field, line)` for loads of a `StoredRelease` field on a stored-release receiver."""
    reads = []
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load)):
            continue
        base = node.value
        receiver = base.id if isinstance(base, ast.Name) else getattr(base, "attr", None)
        if node.attr in STORED_FIELDS and receiver in STORED_RECEIVERS:
            reads.append((node.attr, node.lineno))
    return reads


def test_nothing_outside_the_facade_imports_build_errors():
    rows = src_imports()
    defined = [m for m, path in src_modules() if "class BuildErrors(" in path.read_text("utf-8")]
    assert defined == ["fransys.pipeline"], "the walk did not see BuildErrors"
    assert [
        (r.module, r.line) for r in rows if r.package != FACADE and r.name == "BuildErrors"
    ] == []


def test_nothing_outside_the_facade_branches_on_error_severity():
    seen = 0
    hits = []
    for module, path in src_modules():
        if module.split(".", maxsplit=1)[0] == FACADE or module == HOME:
            continue
        text = path.read_text(encoding="utf-8")
        seen += error_constructions(text)
        hits += [f"{module}:{line}" for line in error_branches(text)]
    assert seen >= 1, "the walk saw no Severity.ERROR"
    assert hits == []


def test_the_facade_reads_no_stored_release_field():
    assert {"folder", "listing", "numbering"} == STORED_FIELDS
    hits = []
    for module, path in src_modules():
        if module.split(".", maxsplit=1)[0] == FACADE:
            hits += [
                f"{module}:{line} .{field}"
                for field, line in stored_field_reads(path.read_text(encoding="utf-8"))
            ]
    assert hits == []


def test_the_build_errors_gate_can_fail():
    forms = [
        "from fransys.pipeline import BuildErrors",
        "from fransys import BuildErrors as B",
        "import fransys.pipeline as p\np.BuildErrors",
    ]
    for source in forms:
        assert buildable_imports(source, "fransys_reports"), source
    assert buildable_imports("from fransys import write", "fransys_reports") == []


def test_the_error_branch_gate_can_fail():
    branches = [
        "if f.severity is Severity.ERROR:\n    pass",
        "x = 1 if f.severity == Severity.ERROR else 2",
        "while a != Severity.ERROR:\n    pass",
        "y = [f for f in fs if f.severity is Severity.ERROR]",
        "z = Severity.ERROR in levels",
        "match s:\n    case Severity.ERROR:\n        pass",
        "from m import Severity as S\nif s is S.ERROR:\n    pass",
    ]
    for source in branches:
        assert error_branches(source), source
    constructions = [
        "f = Finding(code=c, severity=Severity.ERROR)",
        "t = dict(severities=(Severity.ERROR,))",
        "d = {Severity.ERROR: 1}",
    ]
    for source in constructions:
        assert error_branches(source) == [], source
        assert error_constructions(source) == 1, source


def test_the_stored_field_gate_can_fail():
    for field in sorted(STORED_FIELDS):
        for receiver in ("previous", "self.stored", "release"):
            assert stored_field_reads(f"x = {receiver}.{field}"), (receiver, field)
    assert stored_field_reads("previous.listing = 1") == []
    assert stored_field_reads("x = release.path") == []
    assert stored_field_reads("x = rewrite.folder") == []


def test_the_home_of_the_rule_is_what_the_exemption_skips():
    home = next(path for module, path in src_modules() if module == HOME)
    assert error_branches(home.read_text(encoding="utf-8")), "the exemption skips nothing"
