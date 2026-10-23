"""`help KEY` for a finding code and the near-miss suggestion (AGENT-HELP)."""

from fransys._codes import BY_CODE
from fransys._help_codes import lookup_code, suggest


def test_a_code_prints_its_severity_and_its_fix():
    info = BY_CODE["SHEET_FORMAT_UNUSED"]
    text = lookup_code("SHEET_FORMAT_UNUSED")
    assert text is not None
    assert info.fix in text
    assert info.cause in text
    assert info.severities[0].name in text
    assert f"{info.page}.md" in text


def test_an_unknown_code_is_none():
    assert lookup_code("NOT_A_CODE") is None
    assert lookup_code("write") is None


def test_a_near_miss_offers_the_close_name():
    assert "write" in suggest("wrte")
    assert suggest("wrte")[0] == "write"
    assert len(suggest("wrte")) <= 5


def test_a_near_miss_of_a_code_offers_the_code():
    assert "SHEET_FORMAT_UNUSED" in suggest("SHEET_FORMAT_UNUSD")
    assert suggest("zzzzzzzz") == ()
