"""What a stored baseline says: `BASELINE_DIFFERS`, `BASELINE_RULES_MOVED`, `BASELINE_TOO_OLD`.

`release` (nested units) and `verify` share them; the listing is compared under the rules of
the `fransys` release that cut it (LS2, LS3, model-0289), never under today's by default.
"""

from typing import TYPE_CHECKING, cast

from fransys_model.derive import baseline, revision_text
from fransys_model.kernel import Finding, Id, Severity

from ._baseline_cause import sections_text
from ._codes import fix_text
from ._release_reader import manifest_readable, stored_fransys_version

if TYPE_CHECKING:
    from fransys_model.derive.baseline import Listing
    from fransys_model.kernel import Model
    from fransys_model.vocab import Unit as ModelUnit

    from ._release_checks import _ReleaseTarget


def _finding(code: str, severity: Severity, unit: Id[ModelUnit] | None, message: str) -> Finding:
    return Finding(
        code=code,
        severity=severity,
        subjects=(unit,) if unit is not None else (),
        message=message,
        fix=fix_text(code),
    )


def _too_old(unit: Id[ModelUnit] | None, label: str, version: str | None) -> Finding:
    """`BASELINE_TOO_OLD`: the stored baseline's rules are unknown; never compared under today's."""
    oldest = baseline.OLDEST_VERIFIABLE
    cut = (
        "its manifest records no fransys version"
        if version is None
        else f"it was cut by fransys {version}"
    )
    return _finding(
        "BASELINE_TOO_OLD",
        Severity.ERROR,
        unit,
        f"{label} cannot be verified: {cut}; the oldest release this build can verify is {oldest}",
    )


def _moved(
    status: baseline.ListingStatus,
    unit: Id[ModelUnit] | None,
    label: str,
    version: str | None,
    *,
    nested: bool,
) -> Finding:
    """`BASELINE_RULES_MOVED`, or `BASELINE_ROWS_UNCHECKED` when rows could not be rebuilt.

    `nested` makes it an `ERROR`: `release` refuses until `fr.rebaseline` re-cuts the baseline.
    """
    severity = Severity.ERROR if nested else Severity.INFO
    first = "; run fr.rebaseline first" if nested else ""
    cut = f"{label} was released by fransys {version}"
    if status.state == "rules_moved":
        text = f"{cut}; its content is unchanged, and {status.moved_in} changed how it prints"
        return _finding("BASELINE_RULES_MOVED", severity, unit, text + first)
    text = (
        f"{cut}; {status.unchecked} rows hold a contact block numbered before the holder rule "
        f"of fransys {status.moved_in}, which today's numbering cannot print, and were not "
        "compared; the other rows are unchanged"
    )
    return _finding("BASELINE_ROWS_UNCHECKED", severity, unit, text + first)


def status_findings(
    status: baseline.ListingStatus,
    unit: Id[ModelUnit] | None,
    release: _ReleaseTarget,
    *,
    nested: bool,
) -> tuple[Finding, ...]:
    """What a `listing_status` says about `unit`'s stored listing: `()` when it is the same.

    `nested` is `release`'s subtree check: a moved rule or an unchecked row is an `ERROR` there,
    an `INFO` from `verify`. No manifest is not `too_old`.
    """
    version = stored_fransys_version(release.path)
    label = f"{release.name} {revision_text(release.version, release.revision)}"
    if status.state == "same":
        return ()
    if status.state == "too_old":
        return (_too_old(unit, label, version),) if manifest_readable(release.path) else ()
    if status.state in ("rules_moved", "rows_unchecked"):
        return (_moved(status, unit, label, version, nested=nested),)
    sections = sections_text(cast("Listing", status.against), cast("Listing", status.compared))
    return (
        _finding(
            "BASELINE_DIFFERS",
            Severity.ERROR,
            unit,
            f"{label} differs from its released baseline in: {sections}",
        ),
    )


def baseline_findings(
    model: Model,
    unit: Id[ModelUnit] | None,
    release: _ReleaseTarget,
    stored_text: str,
    *,
    nested: bool,
) -> tuple[Finding, ...]:
    """What `stored_text` says about `unit`'s fresh listing: `()` when it holds.

    `stored_text` is not `None`.
    """
    version = stored_fransys_version(release.path)
    status = baseline.listing_status(stored_text, model, unit, version or "")
    return status_findings(status, unit, release, nested=nested)
