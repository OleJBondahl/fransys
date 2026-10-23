"""Part-file finding codes about files and tables (BUILD-MESSAGES M1)."""

from fransys_model.kernel import CodeInfo, Severity

FINDING_CODES: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="TABLE_UNKNOWN",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause=(
            "The file has a top-level table that is neither `schema` nor a part-file table the "
            "contract names."
        ),
        fix=(
            "A top-level table is `schema` or a table the part-file contract names. Write: [part]"
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="TOML_INVALID",
        severities=(Severity.ERROR,),
        stage="library load",
        who="consumer",
        cause="A part-file is not valid TOML.",
        fix=(
            'The file is valid TOML: fix the syntax error the message names. Write: name = "value"'
        ),
        page="findings-validators",
    ),
)
