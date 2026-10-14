"""Part-file finding codes about contacts, rest states and protection (BUILD-MESSAGES M1)."""

from fransys_model.kernel import CodeInfo, Severity

FINDING_CODES: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="CHANGEOVER_LINK",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause=(
            "A `switched` link of a `contact_co` function joins two ports whose roles are not "
            "`common` with `break` or `make`."
        ),
        fix=(
            "Make each `switched` link of the `contact_co` function join a `common` port to a "
            "`break` or `make` port."
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="CHANGEOVER_ROLE",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause=(
            "A port of a `contact_co` function has a `role` other than `common`, `break` or `make`."
        ),
        fix="Set that port's `role` to `common`, `break` or `make`.",
        page="findings-parts",
    ),
    CodeInfo(
        code="CHANGEOVER_SYMBOL_PORT",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A port of a `contact_co` function sets `symbol_port`.",
        fix=(
            "Remove `symbol_port` from the `contact_co` port; the drawing binds a changeover "
            "by its throw roles."
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="CONTACT_WITHOUT_SWITCHED_LINK",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause=(
            "A `contact_no`, `contact_nc`, `contact_co` or `switch` function has no `switched` "
            "link in its `links`."
        ),
        fix=(
            'Add a `links` entry with `kind = "switched"` joining its ports, or change the '
            "function's `kind`."
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="PROTECTION_LINK_KIND",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause=(
            "A `switched` link sits on a `protection` function, or a through link's `kind` "
            "does not fit its protection `type`."
        ),
        fix=(
            'Use `kind = "protective"` for fuse, mcb, motor_breaker and rcd, and `kind = '
            '"conductive"` for overload; never `switched`.'
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="PROTECTION_TYPE_ON_NON_PROTECTION",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause=(
            "A function whose `kind` is not `protection` has a `[function.protection]` table "
            "with a `type`."
        ),
        fix=(
            "Remove the `[function.protection]` table, or change the function's `kind` to "
            "`protection`."
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="PROTECTION_WITHOUT_TYPE",
        severities=(Severity.WARNING,),
        stage="library load",
        who="part author",
        cause="A `protection` function has no `type` in its `[function.protection]` table.",
        fix=(
            "Add `type` to `[function.protection]`, one of fuse, mcb, motor_breaker, overload "
            "or rcd."
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="REST_DISAGREES_WITH_KIND",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause=(
            "A switched link's `rest` disagrees with its function's `kind`: `contact_no` is "
            "open at rest, `contact_nc` is closed."
        ),
        fix=(
            "Set `rest` to match `kind`, `open` for `contact_no` and `closed` for "
            "`contact_nc`, or change `kind`."
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="REST_ON_UNSWITCHED_LINK",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A link whose `kind` is not `switched` sets `rest`.",
        fix="Remove `rest` from the link, or change its `kind` to `switched`.",
        page="findings-parts",
    ),
    CodeInfo(
        code="SWITCHED_LINK_WITHOUT_REST",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A `switched` link of a `switch` or `generic` function sets no `rest`.",
        fix='Add `rest = "open"` or `rest = "closed"` to the link.',
        page="findings-parts",
    ),
    CodeInfo(
        code="SYMBOL_REST_MISMATCH",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause=(
            "A function's `symbol` implies a rest state (`make-contact` open; `break-contact` "
            "and `emergency-stop` closed), and its switched links, stated or implied by its "
            "`kind`, are all at the other one."
        ),
        fix=(
            "Change the `symbol`, or the `rest` of the switched links, so both name the same "
            "rest state."
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="SYMBOL_TYPE_MISMATCH",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause=(
            "A protection function's `symbol` is `fuse` or `circuit-breaker`, but its "
            "protection `type` is another one."
        ),
        fix=(
            "Make `type` match the symbol: `fuse` for `fuse`, `mcb` for `circuit-breaker`, or "
            "change the `symbol`."
        ),
        page="findings-parts",
    ),
)
