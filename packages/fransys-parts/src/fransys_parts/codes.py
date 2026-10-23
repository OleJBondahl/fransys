"""Part-file finding codes about files, tables and fields (BUILD-MESSAGES M1)."""

from fransys_model.kernel import CodeInfo, Severity
from fransys_model.vocab import FINDING_CODES as MODEL_CODES

from . import codes_contacts, codes_files, codes_functions

_OWN: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="BOARD_WITHOUT_PCB",
        severities=(Severity.WARNING,),
        stage="library load",
        who="part author",
        cause='A part with `category = "board"` has no `[pcb]` table.',
        fix=(
            "A board has a `[pcb]` table with a string `revision`, or a `category` other than "
            'board. Write: revision = "A"'
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
            "Each `pairs` entry has two integer `cores` in range, neither `SH` nor in another "
            "pair, and a `screen` that is one unique `SH` core. "
            "Write: pairs = [{{ cores = [1, 2], screen = 3 }}]"
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
            'A `category = "cable"` part has a `[cable_product]` table, and no other part does. '
            "Write: [cable_product]"
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
            "Use 1 to 3 uppercase letters, the first as in IEC 81346-2, such as `K` or `QA`. "
            'Write: class_code = "K"'
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
            "The field takes one of the values the message lists, spelled as the contract gives "
            'them. Write: kind = "load"'
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
            'A `[function.connector]` needs `kind = "connector"`, and a `[function.plc_channel]` '
            'needs `kind = "plc_channel"`. Write: kind = "connector"'
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
            "Each file needs `schema`, its `[part]` table and each required field, with values "
            "the contract allows. Write: schema = 1"
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
            "Write the value as the type the message names, a quoted string for a rating or an "
            "integer for `schema`. Write: schema = 1"
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="FIELD_UNKNOWN",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A table holds a key the part-file contract does not name for that table.",
        fix=(
            "A table takes only the keys the part-file contract names for it. "
            "Write: <contract key> = <same value>"
        ),
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
        fix=(
            "A part file name uses only lowercase letters, digits, hyphens and underscores. "
            "Write: relay-2co-24vdc.toml"
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="FILE_UNREADABLE",
        severities=(Severity.ERROR,),
        stage="library load",
        who="consumer",
        cause="A part-file could not be read (missing file, permission error, or bad encoding).",
        fix=(
            "No call clears this: fix the path, the file permissions or the UTF-8 encoding, then "
            "load again."
        ),
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
        fix=(
            "A number is a quoted string in a part file, never a bare TOML float. "
            'Write: voltage_dc_v = "24.5"'
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="LIBRARY_FILE_MISSING",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="The library root has no `library.toml` file.",
        fix=(
            "The library root holds a `library.toml` with `schema`, `name` and `version`. "
            "Write: schema = 1"
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="MULTILINE_STRING",
        severities=(Severity.ERROR,),
        stage="library load",
        who="consumer",
        cause="A part-file string contains a line break, which the contract forbids.",
        fix=(
            "A string stays on one line; a line break is written as TOML's escaped `\\n`. "
            'Write: description = "one line"'
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="PART_DUPLICATE",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="Two part files declare the same `manufacturer` and `mpn` pair.",
        fix=(
            "Each `manufacturer` and `mpn` pair is declared by one part file only. "
            'Write: mpn = "DEMO-RLY-2CO-24"'
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="PINCOUNT",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A `[function.connector]` has a `pincount` below 1.",
        fix="A connector `pincount` is an integer of 1 or more. Write: pincount = 2",
        page="findings-parts",
    ),
    CodeInfo(
        code="RATING_TABLE_EMPTY",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A `[rating]`, `[function.rating]` or `[function.operating]` table has no field.",
        fix=(
            "A rating table holds at least one value, or the table is deleted. "
            'Write: voltage_dc_v = "24"'
        ),
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
            "Each rating value is a quoted plain decimal, above zero in a rating, and each "
            "breaking point has `voltage_v` and `current_a`. "
            'Write: voltage_dc_v = "24"'
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
            "The file's `schema` is the value `library.toml` names, or both change in one "
            "commit. Write: schema = 1"
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="SCHEMA_UNSUPPORTED",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A `schema` value is not in `SUPPORTED_SCHEMAS`, which today holds only 1.",
        fix="The `schema` is an integer in the supported set, only 1 today. Write: schema = 1",
        page="findings-parts",
    ),
)

FINDING_CODES: tuple[CodeInfo, ...] = (
    *_OWN,
    *codes_files.FINDING_CODES,
    *codes_contacts.FINDING_CODES,
    *codes_functions.FINDING_CODES,
)

# `lint.py` raises two model codes (CABLE_CORE_COUNT, CABLE_WITHOUT_PRODUCT)
_BY_CODE: dict[str, CodeInfo] = {info.code: info for info in (*MODEL_CODES, *FINDING_CODES)}


def fix_text(code: str, **values: str) -> str:
    """The `fix` of one finding of `code`: the code's template filled with `values`."""
    return _BY_CODE[code].filled(**values)
