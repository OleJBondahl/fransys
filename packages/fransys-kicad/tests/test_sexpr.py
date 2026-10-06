"""Direct tests for the s-expression reader (spec section 8; mutmut triage rank 2: no direct
test file existed before, only indirect exercise via bootstrap.py, which never fed it an escape
sequence or a malformed atom)."""

import pytest
from fransys_kicad._sexpr import parse_sexpr


def test_a_real_newline_escape_decodes_to_an_actual_newline():
    assert parse_sexpr('(a "line\\nbreak")') == ["a", "line\nbreak"]


def test_a_backslash_and_a_quote_escape_decode_correctly():
    assert parse_sexpr(r'(a "ba\\ck\"slash")') == ["a", 'ba\\ck"slash']


def test_a_bare_atom_with_no_parens_raises_expected_opening_parenthesis():
    with pytest.raises(ValueError, match="expected an opening parenthesis"):
        parse_sexpr("bare")


def test_nested_lists_parse_into_nested_python_lists():
    assert parse_sexpr('(a (b "c") d)') == ["a", ["b", "c"], "d"]


def test_an_unclosed_parenthesis_raises_its_own_message():
    with pytest.raises(ValueError, match="an unclosed parenthesis"):
        parse_sexpr("(a (b")


def test_a_carriage_return_escape_decodes_to_an_actual_carriage_return():
    assert parse_sexpr('(a "x\\ry")') == ["a", "x\ry"]
