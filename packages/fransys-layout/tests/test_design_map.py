"""Design map check (layout-redesign spec D7), pure AST and markdown parse.

The tables in `docs/rules/*.md` map every public `stages` function to a rule and a test.
A row has three cells: rule, backticked `dotted.module.func` names (first is the rule's
function), backticked `path::test` refs; or four, with a leading rule-id cell naming the
conventions-table rows (decision layout-0111) the rule holds, `-` for none. Every table row's
id is in one doc row, and every doc id is a table row (checks g to i). `design_map_untested.txt`
lists rows with no test yet and only shrinks. The core takes paths so the can-fail tests feed
it tmp trees.
"""

import ast
import re
from pathlib import Path
from typing import NamedTuple

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PACKAGE_ROOT / "src" / "fransys_layout"
CELLS = (3, 4)
TICKS = re.compile(r"`([^`]+)`")


class Row(NamedTuple):
    """One table row: its functions (first is the rule's), its test refs and its rule ids."""

    funcs: list[str]
    tests: list[str]
    ids: list[str] = []  # noqa: RUF012 -- a NamedTuple default, never mutated


def _parse_line(line: str) -> Row | None:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return None
    cells = [c.strip() for c in stripped.strip("|").split("|")]
    if len(cells) not in CELLS or "`" not in cells[-2]:
        return None
    ids = re.findall(r"[A-Za-z][\w.]*", cells[0]) if len(cells) == max(CELLS) else []
    return Row(TICKS.findall(cells[-2]), TICKS.findall(cells[-1]), ids)


def parse_rows(rules_dir: Path) -> list[Row]:
    """Every table row of every `*.md` in `rules_dir`; none when the folder is missing."""
    if not rules_dir.is_dir():
        return []
    lines = [
        line
        for md in sorted(rules_dir.glob("*.md"))
        for line in md.read_text(encoding="utf-8").splitlines()
    ]
    return [row for row in map(_parse_line, lines) if row]


def _top_defs(body: list[ast.stmt]) -> set[str]:
    kinds = (ast.FunctionDef, ast.AsyncFunctionDef)
    return {node.name for node in body if isinstance(node, kinds)}


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def function_exists(stages_root: Path, dotted: str) -> bool:
    """True when `dotted` names a top-level def of a stages module or package, or of `geometry`."""
    *module, func = dotted.split(".")
    if not module:
        return False
    root = stages_root.parent if module[0] == "geometry" else stages_root
    base = root.joinpath(*module)
    for candidate in (base.with_suffix(".py"), base / "__init__.py"):
        if candidate.is_file():
            return func in _top_defs(_parse(candidate).body)
    return False


def ref_exists(package_root: Path, ref: str) -> bool:
    """True when `path::test` or `path::Class::test` resolves by AST; `[param]` is stripped."""
    path, *rest = re.sub(r"\[.*\]$", "", ref).split("::")
    file = package_root / path
    if not file.is_file() or not 1 <= len(rest) <= 2:
        return False
    body = _parse(file).body
    if len(rest) == 2:
        classes = [n for n in body if isinstance(n, ast.ClassDef) and n.name == rest[0]]
        if not classes:
            return False
        body = classes[0].body
    return rest[-1] in _top_defs(body)


def public_functions(stages_root: Path) -> set[str]:
    """Dotted names of public top-level defs under stages, `types.py` files excluded."""
    found: set[str] = set()
    for py in sorted(stages_root.rglob("*.py")):
        if py.name == "types.py":
            continue
        parts = list(py.relative_to(stages_root).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        found |= {
            ".".join([*parts, name])
            for name in _top_defs(_parse(py).body)
            if not name.startswith("_")
        }
    return found


def read_allow(allow_file: Path) -> set[str]:
    """Entries of the allow-list; `#` starts a comment; a missing file is empty."""
    if not allow_file.is_file():
        return set()
    lines = allow_file.read_text(encoding="utf-8").splitlines()
    return {entry for line in lines if (entry := line.split("#")[0].strip())}


def _exist_problems(rows: list[Row], stages_root: Path, package_root: Path) -> list[str]:
    problems = [
        f"(a) function {name} not found"
        for row in rows
        for name in row.funcs
        if not function_exists(stages_root, name)
    ]
    problems += [
        f"(b) test {ref} not found"
        for row in rows
        for ref in row.tests
        if not ref_exists(package_root, ref)
    ]
    return problems


def _coverage_problems(rows: list[Row], stages_root: Path) -> list[str]:
    named = [name for row in rows for name in row.funcs]
    problems = [
        f"(c) public function {name} is in no row"
        for name in sorted(public_functions(stages_root) - set(named))
    ]
    problems += [
        f"(d) function {name} is named {named.count(name)} times"
        for name in sorted(set(named))
        if named.count(name) > 1
    ]
    return problems


def _allow_problems(rows: list[Row], allow: set[str]) -> list[str]:
    firsts = {row.funcs[0] for row in rows}
    tested = {row.funcs[0] for row in rows if row.tests}
    problems = [
        f"(e) rule {row.funcs[0]} has no test and is not on the allow-list"
        for row in rows
        if not row.tests and row.funcs[0] not in allow
    ]
    problems += [
        f"(f) allow-list entry {entry} is stale: "
        + ("its row has a test" if entry in tested else "it is the first function of no row")
        for entry in sorted(allow)
        if entry in tested or entry not in firsts
    ]
    return problems


def _id_problems(rows: list[Row], table_ids: list[str]) -> list[str]:
    doc_ids = [i for row in rows for i in row.ids]
    problems = [
        f"(g) table row {i} is in no doc row's id cell"
        for i in sorted(set(table_ids) - set(doc_ids))
    ]
    problems += [f"(h) doc id {i} is no table row" for i in sorted(set(doc_ids) - set(table_ids))]
    problems += [f"(i) rule id {i} has no test" for row in rows if not row.tests for i in row.ids]
    problems += [
        f"(j) table row id {i} is used twice"
        for i in sorted(set(table_ids))
        if table_ids.count(i) > 1
    ]
    return problems


def check_design_map(
    rules_dir: Path,
    stages_root: Path,
    package_root: Path,
    allow_file: Path,
    table_ids: list[str] | None = None,
) -> list[str]:
    """Every problem (a) to (j) of the design map; empty when the map holds.

    `table_ids` is every row id of the conventions tables; None skips checks (g), (h) and (j).
    """
    rows = parse_rows(rules_dir)
    return [
        *_exist_problems(rows, stages_root, package_root),
        *_coverage_problems(rows, stages_root),
        *_allow_problems(rows, read_allow(allow_file)),
        *([] if table_ids is None else _id_problems(rows, table_ids)),
    ]


# ---- tests ----

ROW_ONE = "| rule one | `columns.replica_key`, `columns.helper` | `tests/test_x.py::test_a` |"
ROW_TWO = "| rule two | `refs.refs_main` | `tests/test_x.py::TestK::test_b[p]` |"
ROW_THREE = "| rule three | `columns.untested` | - |"
HEADER = ["| Rule | Function | Test |", "| --- | --- | --- |"]


def _build(
    root: Path,
    rows: tuple[str, ...],
    allow: str = "columns.untested",
    table_ids: list[str] | None = None,
) -> list[str]:
    """Write a tiny tree under `root` and return the design map problems of it."""
    stages = root / "stages"
    (stages / "refs").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "rules").mkdir()
    (stages / "columns.py").write_text(
        "def replica_key(): ...\ndef helper(): ...\ndef untested(): ...\ndef _private(): ...\n"
    )
    (stages / "refs" / "__init__.py").write_text("def refs_main(): ...\n")
    (stages / "types.py").write_text("def ignored_public(): ...\n")
    (root / "tests" / "test_x.py").write_text(
        "def test_a(): ...\nclass TestK:\n    def test_b(self): ...\n"
    )
    (root / "rules" / "r.md").write_text("\n".join([*HEADER, *rows]))
    (root / "allow.txt").write_text(f"# header\n\n{allow}  # why\n")
    return check_design_map(root / "rules", stages, root, root / "allow.txt", table_ids)


CLEAN = (ROW_ONE, ROW_TWO, ROW_THREE)


def test_clean_tree_reports_nothing(tmp_path: Path) -> None:
    """The base tree of the can-fail tests is clean, so each injection is the cause."""
    assert _build(tmp_path, CLEAN) == []


def test_parser_reads_two_functions_and_two_tests(tmp_path: Path) -> None:
    """A row with two names and two refs yields both lists, in order; other lines are skipped."""
    md = tmp_path / "r.md"
    md.write_text(
        "text\n| Rule | Function | Test |\n| --- | --- | --- |\n"
        "| r | `a.f`, `a.g` `a.h` | `t.py::x`, `t.py::C::y` |\n| two | cells |\n"
    )
    assert parse_rows(tmp_path) == [Row(["a.f", "a.g", "a.h"], ["t.py::x", "t.py::C::y"], [])]


def test_parser_reads_the_rule_id_cell_of_a_four_cell_row(tmp_path: Path) -> None:
    """A four-cell row's first cell is its ids; `-` is none; the other cells read as before."""
    md = tmp_path / "r.md"
    md.write_text("| V1a, V1b | rule | `a.f` | `t.py::x` |\n| - | rule | `a.g` | `t.py::y` |\n")
    assert parse_rows(tmp_path) == [
        Row(["a.f"], ["t.py::x"], ["V1a", "V1b"]),
        Row(["a.g"], ["t.py::y"], []),
    ]


def test_a_missing_function_is_reported(tmp_path: Path) -> None:
    """(a) A row naming a function that is not a top-level def."""
    bad = ROW_ONE.replace("columns.helper", "columns.nope")
    assert "(a) function columns.nope not found" in _build(tmp_path, (bad, ROW_TWO, ROW_THREE))


def test_b_missing_test_is_reported(tmp_path: Path) -> None:
    """(b) A row citing a test that is not there."""
    bad = ROW_TWO.replace("TestK::test_b", "TestK::test_gone")
    problems = _build(tmp_path, (ROW_ONE, bad, ROW_THREE))
    assert "(b) test tests/test_x.py::TestK::test_gone[p] not found" in problems


def test_c_unmapped_public_function_is_reported(tmp_path: Path) -> None:
    """(c) A public stages function in no row; privates and types.py are not public."""
    bad = ROW_ONE.replace(", `columns.helper`", "")
    assert _build(tmp_path, (bad, ROW_TWO, ROW_THREE)) == [
        "(c) public function columns.helper is in no row"
    ]


def test_d_function_named_twice_is_reported(tmp_path: Path) -> None:
    """(d) A function named in two rows."""
    bad = ROW_TWO.replace("`refs.refs_main`", "`refs.refs_main`, `columns.helper`")
    assert "(d) function columns.helper is named 2 times" in _build(
        tmp_path, (ROW_ONE, bad, ROW_THREE)
    )


def test_e_untested_rule_off_the_allow_list_is_reported(tmp_path: Path) -> None:
    """(e) A row with no test whose first function is not allowed."""
    problems = _build(tmp_path, CLEAN, allow="")
    assert problems == ["(e) rule columns.untested has no test and is not on the allow-list"]


def test_f_stale_allow_entries_are_reported(tmp_path: Path) -> None:
    """(f) An allow entry whose row has a test, and one that is the first function of no row."""
    problems = _build(tmp_path, CLEAN, allow="columns.untested\ncolumns.replica_key\ncolumns.ghost")
    assert problems == [
        "(f) allow-list entry columns.ghost is stale: it is the first function of no row",
        "(f) allow-list entry columns.replica_key is stale: its row has a test",
    ]


ID_ONE = "| T1.1 | rule one | `columns.replica_key`, `columns.helper` | `tests/test_x.py::test_a` |"
ID_TWO = "| T1.2 | rule two | `refs.refs_main` | `tests/test_x.py::TestK::test_b[p]` |"
ID_NONE = "| T1.2 | rule three | `columns.untested` | - |"


def test_ids_both_ways_hold_on_a_clean_tree(tmp_path: Path) -> None:
    """Every table row id is in a doc id cell and the reverse: no problem."""
    assert _build(tmp_path, (ID_ONE, ID_TWO, ROW_THREE), table_ids=["T1.1", "T1.2"]) == []


def test_g_a_table_row_with_no_doc_id_is_reported(tmp_path: Path) -> None:
    """(g) A table row whose id no doc row names."""
    problems = _build(tmp_path, (ID_ONE, ROW_TWO, ROW_THREE), table_ids=["T1.1", "T1.2"])
    assert problems == ["(g) table row T1.2 is in no doc row's id cell"]


def test_h_a_doc_id_that_is_no_table_row_is_reported(tmp_path: Path) -> None:
    """(h) A doc id with no table row behind it."""
    problems = _build(tmp_path, (ID_ONE, ID_TWO, ROW_THREE), table_ids=["T1.1"])
    assert problems == ["(h) doc id T1.2 is no table row"]


def test_i_a_doc_row_with_an_id_and_no_test_is_reported(tmp_path: Path) -> None:
    """(i) Deleting a conventions row's test fails, with no allow-list to excuse it."""
    problems = _build(
        tmp_path, (ID_ONE, ID_NONE), allow="columns.untested", table_ids=["T1.1", "T1.2"]
    )
    assert "(i) rule id T1.2 has no test" in problems


def test_j_a_table_row_id_used_twice_is_reported(tmp_path: Path) -> None:
    """(j) Two table rows with one id."""
    problems = _build(tmp_path, (ID_ONE, ID_TWO, ROW_THREE), table_ids=["T1.1", "T1.2", "T1.2"])
    assert problems == ["(j) table row id T1.2 is used twice"]


def test_a_geometry_function_resolves_beside_the_stages_ones() -> None:
    """A `geometry.` name is read from the geometry folder; an absent name is not found."""
    stages = SRC_ROOT / "stages"
    assert function_exists(stages, "geometry.exits.port_exit")
    assert not function_exists(stages, "geometry.exits.no_such_function")
