"""TEXT-JOINS (spec NUMBER-SORT K16, order NS-8): a printed text built from row fields is found.

Each case is a synthetic module; the scan is proved able to fail on every site shape it counts.
"""

import ast

import pytest
from test_one_home import compare, load_allowlist, scan_tree
from text_joins_scan import text_joins

REPORTS = "fransys_reports.changes"


def _scan(body: str, module: str = REPORTS) -> list[tuple[str, int]]:
    return text_joins(ast.parse(body), module)


def test_an_fstring_of_two_row_fields_is_a_site() -> None:
    assert _scan('def f(row):\n    return f"{row.a} {row.b}"') == [("f", 2)]


def test_an_fstring_of_a_row_field_and_a_literal_is_a_site() -> None:
    assert _scan('def f(row):\n    return f"{row.a} pcs"') == [("f", 2)]


def test_a_join_of_two_row_fields_is_a_site() -> None:
    assert _scan('def f(row):\n    return " ".join((row.a, row.b))') == [("f", 2)]


def test_a_plus_chain_counts_once() -> None:
    assert _scan('def f(row):\n    return row.a + " " + row.b') == [("f", 2)]


def test_a_loop_variable_is_a_row() -> None:
    assert _scan('def f(rows):\n    return [f"{r.a}/{r.b}" for r in rows]') == [("f", 2)]


def test_a_join_of_two_locals_is_no_site() -> None:
    assert _scan('def f(a, b):\n    return " ".join((a, b))') == []
    assert _scan('def f(a, b):\n    return f"{a} {b}"') == []


def test_one_attribute_alone_is_no_site() -> None:
    assert _scan('def f(row):\n    return f"{row.a}"') == []
    assert _scan('def f(row):\n    return ", ".join(x.name for x in row.items)') == []


def test_self_and_a_number_are_no_row() -> None:
    assert _scan('class C:\n    def f(self):\n        return f"{self.a} {self.b}"') == []
    assert _scan("def f(row):\n    return row.a + 1") == []


def test_a_module_outside_the_scope_is_no_site() -> None:
    body = 'def f(row):\n    return f"{row.a} {row.b}"'
    assert _scan(body, "fransys_model.derive.x") == []
    assert _scan(body, "fransys_layout.x") == []
    assert _scan(body, "fransys_pdf.x") == [("f", 2)]
    assert _scan(body, "fransys.build") == [("f", 2)]


def test_a_direct_raise_argument_is_skipped_and_a_finding_message_counts() -> None:
    raising = 'def f(row):\n    raise ValueError(f"bad {row.a} {row.b}")'
    assert _scan(raising) == []
    finding = 'def f(row):\n    return Finding(message=f"bad {row.a} {row.b}")'
    assert _scan(finding) == [("f", 2)]


def test_a_message_assigned_then_raised_is_no_site() -> None:
    body = 'def f(row):\n    msg = f"bad {row.a} {row.b}"\n    raise ValueError(msg)'
    assert _scan(body) == []
    unraised = 'def f(row):\n    msg = f"bad {row.a} {row.b}"\n    return msg'
    assert _scan(unraised) == [("f", 2)]


@pytest.mark.private_input  # a private-gate count (R462)
def test_the_text_join_stock_matches_one_home_toml() -> None:
    assert compare(scan_tree(text_joins), load_allowlist()["text_joins"]) == []
