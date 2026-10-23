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
            "Each `switched` link of a `contact_co` joins its `common` port to a `break` or "
            '`make` port. Write: links = [{{ a = "11", b = "12", kind = "switched" }}]'
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
        fix=(
            'A `contact_co` port takes the role `common`, `break` or `make`. Write: role = "common"'
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="CHANGEOVER_SYMBOL_PORT",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A port of a `contact_co` function sets `symbol_port`.",
        fix=(
            "A `contact_co` port takes no `symbol_port`, since its throw roles bind the drawing. "
            'Write: {{ name = "12", role = "break" }}'
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
            "A contact or switch function has a `switched` link joining two of its ports, or a "
            'different `kind`. Write: links = [{{ a = "1", b = "2", kind = "switched" }}]'
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
            "A fuse, mcb, motor_breaker or rcd link is `protective`, an overload link is "
            '`conductive`, never `switched`. Write: kind = "protective"'
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
            "Only a `protection` function has a `[function.protection]` table with a `type`. "
            'Write: kind = "protection"'
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
            "`[function.protection]` needs a `type`: fuse, mcb, motor_breaker, overload or rcd. "
            'Write: type = "mcb"'
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
            "`rest` is `open` for `contact_no` and `closed` for `contact_nc`, or change `kind`. "
            'Write: rest = "open"'
        ),
        page="findings-parts",
    ),
    CodeInfo(
        code="REST_ON_UNSWITCHED_LINK",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A link whose `kind` is not `switched` sets `rest`.",
        fix='Only a `switched` link takes `rest`. Write: kind = "switched"',
        page="findings-parts",
    ),
    CodeInfo(
        code="SWITCHED_LINK_WITHOUT_REST",
        severities=(Severity.ERROR,),
        stage="library load",
        who="part author",
        cause="A `switched` link of a `switch` or `generic` function sets no `rest`.",
        fix=(
            "A `switched` link of a `switch` or `generic` function states its `rest`. "
            'Write: rest = "open"'
        ),
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
            "The symbol and the switched links agree on one rest state: make-contact is open, "
            'break-contact and emergency-stop are closed. Write: rest = "open"'
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
            'A `fuse` symbol needs `type = "fuse"`, a `circuit-breaker` symbol needs '
            '`type = "mcb"`. Write: type = "fuse"'
        ),
        page="findings-parts",
    ),
)
