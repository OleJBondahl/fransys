"""Part-file finding codes about files, tables and fields (BUILD-MESSAGES M1)."""

from fransys_model.kernel import CodeInfo, Severity

from . import codes_contacts, codes_functions

_OWN: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="BOARD_WITHOUT_PCB",
        severities=(Severity.WARNING,),
        stage="library load",
        who="part author",
        cause='A part with `category = "board"` has no `[pcb]` table.',
        fix=(
            "Add a `[pcb]` table with a `revision` string, or change `category` to the part's "
            "real category."
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="CABLE_PAIR_INVALID",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause=(
            "A `[cable_product]` `pairs` entry breaks a pair rule: a core is out of range, in "
            "two pairs, or `SH`, or a `screen` is not a unique `SH` core."
        ),
        fix=(
            "Give each `pairs` entry two integer `cores` in range, none `SH` and none in "
            "another pair, and a `screen` that is one unique `SH` core."
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="CABLE_WITHOUT_PRODUCT",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause=(
            'A part with `category = "cable"` has no `[cable_product]` table, or a part with '
            "another category has one."
        ),
        fix=(
            "Add a `[cable_product]` table to a cable part, or remove `[cable_product]` from a "
            "part whose `category` is not `cable`."
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="CLASS_CODE",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause=(
            "`class_code` is not 1 to 3 uppercase letters, starts with A, I or O, or starts "
            "with D, L, V, Y or Z."
        ),
        fix=(
            "Set `class_code` to 1 to 3 uppercase letters, first letter as in IEC 81346-2, "
            "such as `K` or `QA`."
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="ENUM_VALUE",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A field typed as an enum holds a string that is no member of that enum.",
        fix=(
            "Set the field to one of the values the message lists, such as a `kind` or `role` "
            "value."
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="FACET_KIND_MISMATCH",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause=(
            "A `[function.connector]` sits on a function whose `kind` is not `connector`, or a "
            "`[function.plc_channel]` on one whose `kind` is not `plc_channel`."
        ),
        fix=(
            "Change the function's `kind` to match the sub-table, or move the sub-table to the "
            "right `[[function]]`."
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="FIELD_MISSING",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause=(
            "A required key is absent: the file's `schema`, its `[part]` table, or a required "
            "field of a table."
        ),
        fix=(
            "Add the `schema = 1` line, the `[part]` table, or the required field the message "
            "names."
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="FIELD_TYPE",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause=(
            "A value has a TOML type the contract does not allow there, such as an integer for "
            "a quantity or a table where a list belongs."
        ),
        fix=(
            "Write the value as the type the message names, such as a quoted string for a "
            "rating or an integer for `schema`."
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="FIELD_UNKNOWN",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A table holds a key the part-file contract does not name for that table.",
        fix="Remove the key, or correct its spelling to a field the part-file contract names.",
        page="findings-parts",
    ),
    CodeInfo(
        code="FILE_NAME",
        severities=(Severity.WARNING,),
        stage="library load",
        who="part author",
        cause=(
            "A part file's name has characters other than lowercase letters, digits, hyphens "
            "and underscores."
        ),
        fix="Rename the file using only lowercase letters, digits, hyphens and underscores.",
        page="findings-parts",
    ),
    CodeInfo(
        code="FILE_UNREADABLE",
        severities=(Severity.ERROR,),
        stage="library load",
        who="consumer",
        cause="A part-file could not be read (missing file, permission error, or bad encoding).",
        fix="Fix the path, permissions or encoding (UTF-8).",
        page="findings-validators",
    ),
    CodeInfo(
        code="FLOAT_FORBIDDEN",
        severities=(Severity.ERROR,),
        stage="library load",
        who="consumer",
        cause=(
            "A part-file has a bare TOML float, which the contract forbids (quote values as "
            "strings)."
        ),
        fix="Quote the numeric value as a string.",
        page="findings-validators",
    ),
    CodeInfo(
        code="LIBRARY_FILE_MISSING",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="The library root has no `library.toml` file.",
        fix="Add `library.toml` at the library package root with `schema`, `name` and `version`.",
        page="findings-parts",
    ),
    CodeInfo(
        code="MULTILINE_STRING",
        severities=(Severity.ERROR,),
        stage="library load",
        who="consumer",
        cause="A part-file string contains a line break, which the contract forbids.",
        fix="Use a single-line string, or TOML's escaped `\\n`.",
        page="findings-validators",
    ),
    CodeInfo(
        code="PART_DUPLICATE",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="Two part files declare the same `manufacturer` and `mpn` pair.",
        fix=(
            "Remove one of the files, or correct the `mpn` or `manufacturer` of the one "
            "declared in error."
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="PINCOUNT",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A `[function.connector]` has a `pincount` below 1.",
        fix="Set `pincount` to 1 or more.",
        page="findings-parts",
    ),
    CodeInfo(
        code="RATING_TABLE_EMPTY",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A `[rating]`, `[function.rating]` or `[function.operating]` table has no field.",
        fix="Add at least one value to the table, or delete the table.",
        page="findings-parts",
    ),
    CodeInfo(
        code="RATING_VALUE_INVALID",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause=(
            "A rating value is not a plain decimal string, is zero where a rating needs a "
            "positive value, or a breaking point list is malformed."
        ),
        fix=(
            'Write each value as a quoted plain decimal such as "24", above zero in ratings, '
            "and each breaking point with `voltage_v` and `current_a`."
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="SCHEMA_MIXED",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A part file's `schema` differs from the `schema` in its library's `library.toml`.",
        fix=(
            "Set the file's `schema` to the value `library.toml` names, or change "
            "`library.toml` and every file in one commit."
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="SCHEMA_UNSUPPORTED",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A `schema` value is not in `SUPPORTED_SCHEMAS`, which today holds only 1.",
        fix="Set `schema = 1`, the only supported value today.",
        page="findings-parts",
    ),
    CodeInfo(
        code="TABLE_UNKNOWN",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause=(
            "The file has a top-level table that is neither `schema` nor a part-file table the "
            "contract names."
        ),
        fix="Remove the table, or rename it to a table the part-file contract names.",
        page="findings-parts",
    ),
    CodeInfo(
        code="TOML_INVALID",
        severities=(Severity.ERROR,),
        stage="library load",
        who="consumer",
        cause="A part-file is not valid TOML.",
        fix="Fix the TOML syntax error named.",
        page="findings-validators",
    ),
)

FINDING_CODES: tuple[CodeInfo, ...] = (
    *_OWN,
    *codes_contacts.FINDING_CODES,
    *codes_functions.FINDING_CODES,
)
