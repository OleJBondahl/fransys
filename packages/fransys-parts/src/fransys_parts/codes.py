"""Part-file finding codes about files, tables and fields (BUILD-MESSAGES M1)."""

from typing import Any
lazy from collections.abc import Iterable

from fransys_model.kernel import CodeInfo, Finding, Id, Severity
from fransys_model.vocab import FINDING_CODES as MODEL_CODES

from . import codes_contacts, codes_files, codes_functions

_OWN: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="BOARD_WITHOUT_PCB",
        severity=Severity.WARNING,
        stage="library load",
        who="part author",
        cause='A part with `category = "board"` has no `[pcb]` table.',
        fix=('A board has a `[pcb]` table with a string `revision`, or a `category` other than board. Write: revision = "A"'),
        page="findings-parts",
    ),
    CodeInfo(
        code="CABLE_PAIR_INVALID",
        severity=Severity.ERROR,
        stage="library load",
        who="part author",
        cause=(
            "A `[cable_product]` `pairs` entry breaks a pair rule: a core is out of range, in "
            "two pairs, or `SH`, or a `screen` is not a unique `SH` core."
        ),
        fix=(
            "Each `pairs` entry has two integer `cores` in range, neither `SH` nor in another "
            "pair, and a `screen` that is one unique `SH` core. "
            "Write: pairs = [{{ cores = [1, 2], screen = 3 }}]"
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="CABLE_WITHOUT_PRODUCT",
        severity=Severity.ERROR,
        stage="library load",
        who="part author",
        cause=('A part with `category = "cable"` has no `[cable_product]` table, or a part with another category has one.'),
        fix=('A `category = "cable"` part has a `[cable_product]` table, and no other part does. Write: [cable_product]'),
        page="findings-parts",
    ),
    CodeInfo(
        code="CLASS_CODE",
        severity=Severity.ERROR,
        stage="library load",
        who="part author",
        cause=("`class_code` is not 1 to 3 uppercase letters, starts with A, I or O, or starts with D, L, V, Y or Z."),
        fix=('Use 1 to 3 uppercase letters, the first as in IEC 81346-2, such as `K` or `QA`. Write: class_code = "K"'),
        page="findings-parts",
    ),
    CodeInfo(
        code="ENUM_VALUE",
        severity=Severity.ERROR,
        stage="library load",
        who="part author",
        cause="A field typed as an enum holds a string that is no member of that enum.",
        fix=('The field takes one of the values the message lists, spelled as the contract gives them. Write: kind = "load"'),
        page="findings-parts",
    ),
    CodeInfo(
        code="FACET_KIND_MISMATCH",
        severity=Severity.ERROR,
        stage="library load",
        who="part author",
        cause=(
            "A `[function.connector]` sits on a function whose `kind` is not `connector`, or a "
            "`[function.plc_channel]` on one whose `kind` is not `plc_channel`."
        ),
        fix=(
            'A `[function.connector]` needs `kind = "connector"`, and a `[function.plc_channel]` '
            'needs `kind = "plc_channel"`. Write: kind = "connector"'
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="FIELD_MISSING",
        severity=Severity.ERROR,
        stage="library load",
        who="part author",
        cause=("A required key is absent: the file's `schema`, its `[part]` table, or a required field of a table."),
        fix=("Each file needs `schema`, its `[part]` table and each required field, with values the contract allows. Write: schema = 2"),
        page="findings-parts",
    ),
    CodeInfo(
        code="FIELD_TYPE",
        severity=Severity.ERROR,
        stage="library load",
        who="part author",
        cause=("A value has a TOML type the contract does not allow there, such as an integer for a quantity or a table where a list belongs."),
        fix=("Write the value as the type the message names, a quoted string for a rating or an integer for `schema`. Write: schema = 2"),
        page="findings-parts",
    ),
    CodeInfo(
        code="FIELD_UNKNOWN",
        severity=Severity.ERROR,
        stage="library load",
        who="part author",
        cause="A table holds a key the part-file contract does not name for that table.",
        fix=("A table takes only the keys the part-file contract names for it. Write: <contract key> = <same value>"),
        page="findings-parts",
    ),
    CodeInfo(
        code="FILE_NAME",
        severity=Severity.WARNING,
        stage="library load",
        who="part author",
        cause=("A part file's name has characters other than lowercase letters, digits, hyphens and underscores."),
        fix=("A part file name uses only lowercase letters, digits, hyphens and underscores. Write: relay-2co-24vdc.toml"),
        page="findings-parts",
    ),
    CodeInfo(
        code="FILE_UNREADABLE",
        severity=Severity.ERROR,
        stage="library load",
        who="consumer",
        cause="A part-file could not be read (missing file, permission error, or bad encoding).",
        fix=("No call clears this: fix the path, the file permissions or the UTF-8 encoding, then load again."),
        page="findings-validators",
    ),
    CodeInfo(
        code="FLOAT_FORBIDDEN",
        severity=Severity.ERROR,
        stage="library load",
        who="consumer",
        cause=("A part-file has a bare TOML float, which the contract forbids (quote values as strings)."),
        fix=('A number is a quoted string in a part file, never a bare TOML float. Write: nominal_current = "24.5 A"'),
        page="findings-validators",
    ),
    CodeInfo(
        code="LIBRARY_FILE_MISSING",
        severity=Severity.ERROR,
        stage="library load",
        who="part author",
        cause="The library root has no `library.toml` file.",
        fix=("The library root holds a `library.toml` with `schema`, `name` and `version`. Write: schema = 2"),
        page="findings-parts",
    ),
    CodeInfo(
        code="MULTILINE_STRING",
        severity=Severity.ERROR,
        stage="library load",
        who="consumer",
        cause="A part-file string contains a line break, which the contract forbids.",
        fix=('A string stays on one line; a line break is written as TOML\'s escaped `\\n`. Write: description = "one line"'),
        page="findings-validators",
    ),
    CodeInfo(
        code="PART_DUPLICATE",
        severity=Severity.ERROR,
        stage="library load",
        who="part author",
        cause="Two part files declare the same `manufacturer` and `mpn` pair.",
        fix=('Each `manufacturer` and `mpn` pair is declared by one part file only. Write: mpn = "DEMO-RLY-2CO-24"'),
        page="findings-parts",
    ),
    CodeInfo(
        code="PINCOUNT",
        severity=Severity.ERROR,
        stage="library load",
        who="part author",
        cause="A `[function.connector]` has a `pincount` below 1.",
        fix="A connector `pincount` is an integer of 1 or more. Write: pincount = 2",
        page="findings-parts",
    ),
    CodeInfo(
        code="RATING_TABLE_EMPTY",
        severity=Severity.ERROR,
        stage="library load",
        who="part author",
        cause="A `[rating]`, `[function.rating]` or `[function.operating]` table has no field.",
        fix=('A rating table holds at least one value, or the table is deleted. Write: voltage = [{{ nom = "24 V", at = ["DC"] }}]'),
        page="findings-parts",
    ),
    CodeInfo(
        code="RATING_VALUE_INVALID",
        severity=Severity.ERROR,
        stage="library load",
        who="part author",
        cause=(
            "A figure or quantity is not written as schema 2 asks: a quantity is a number, a space and a unit symbol, and a figure an inline table."
        ),
        fix=(
            'Write each quantity as a string such as "24 V", above zero in a rating, and each '
            "figure as an inline table. "
            'Write: voltage = [{{ nom = "24 V", at = ["DC"] }}]'
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="PART_SCHEMA_OLD",
        severity=Severity.ERROR,
        stage="library load",
        who="part author",
        cause="A part file or `library.toml` is written in schema 1.",
        fix=("Run `python -m fransys migrate-parts DIR` on the library folder; it rewrites each schema 1 file to schema 2. Write: schema = 2"),
        page="findings-parts",
    ),
    CodeInfo(
        code="SCHEMA_MIXED",
        severity=Severity.ERROR,
        stage="library load",
        who="part author",
        cause="A part file's `schema` differs from the `schema` in its library's `library.toml`.",
        fix=("The file's `schema` is the value `library.toml` names, or both change in one commit. Write: schema = 2"),
        page="findings-parts",
    ),
    CodeInfo(
        code="SCHEMA_UNSUPPORTED",
        severity=Severity.ERROR,
        stage="library load",
        who="part author",
        cause="A `schema` value is not in `SUPPORTED_SCHEMAS`, which today holds only 2.",
        fix="The `schema` is an integer in the supported set, only 2 today. Write: schema = 2",
        page="findings-parts",
    ),
)

FINDING_CODES: tuple[CodeInfo, ...] = (
    *_OWN,
    *codes_files.FINDING_CODES,
    *codes_contacts.FINDING_CODES,
    *codes_functions.FINDING_CODES,
)

# `lint.py` raises one model code (CABLE_WITHOUT_PRODUCT)
_BY_CODE: dict[str, CodeInfo] = {info.code: info for info in (*MODEL_CODES, *FINDING_CODES)}


def finding(code: str, subjects: Iterable[Id[Any]], message: str, **fix_values: str) -> Finding:
    """The `Finding` of `code`: its one severity, its fix filled from `fix_values`."""
    return _BY_CODE[code].finding(subjects, message, **fix_values)
