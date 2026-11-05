"""Part-file finding codes about files and tables (BUILD-MESSAGES M1)."""

from fransys_model.kernel import CodeInfo, Severity

FINDING_CODES: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="CABLE_PRODUCT_CORE_COUNT",
        severity=Severity.ERROR,
        stage="library load",
        who="part author",
        cause="A cable product's `core_count` differs from the number of its `core_colours`.",
        fix=('Make `core_count` equal the number of `core_colours`. Write: core_colours = ["BN", "BU"]'),
        page="findings-parts",
    ),
    CodeInfo(
        code="TABLE_UNKNOWN",
        severity=Severity.ERROR,
        stage="library load",
        who="part author",
        cause=("The file has a top-level table that is neither `schema` nor a part-file table the contract names."),
        fix=("A top-level table is `schema` or a table the part-file contract names. Write: [part]"),
        page="findings-parts",
    ),
    CodeInfo(
        code="TOML_INVALID",
        severity=Severity.ERROR,
        stage="library load",
        who="consumer",
        cause="A part-file is not valid TOML.",
        fix=('The file is valid TOML: fix the syntax error the message names. Write: name = "value"'),
        page="findings-validators",
    ),
)
