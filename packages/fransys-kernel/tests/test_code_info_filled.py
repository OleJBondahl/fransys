"""`CodeInfo.filled` gives one finding's fix text and refuses a missing value (AD9)."""

import pytest

from fransys_kernel import CodeInfo, SchemaError, Severity


def _info(fix: str) -> CodeInfo:
    return CodeInfo(
        code="SOME_CODE",
        severities=(Severity.ERROR,),
        stage="build",
        who="consumer",
        cause="c",
        fix=fix,
        page="findings",
    )


def test_filled_puts_the_values_into_the_template() -> None:
    text = _info("Use {valid}. Write: {subject}.spare()").filled(subject="AI1", valid="a tag")
    assert text == "Use a tag. Write: AI1.spare()"


def test_a_missing_value_raises_naming_the_code() -> None:
    with pytest.raises(SchemaError, match=r"SOME_CODE.*'subject'"):
        _info("Write: {subject}").filled(valid="x")
