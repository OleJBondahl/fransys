"""The one map from a core `Finding` to the kernel's (P6.1 D; DRAWING-VALUE reads it too).

The code's severity and fix come from `fransys_el.FINDING_CODES` and `fransys_layout.FINDING_CODES`;
the core carries only text.
"""

from typing import TYPE_CHECKING

from fransys_layout import FINDING_CODES as LAYOUT_CODES
from fransys_model.kernel import Finding as KernelFinding

from .codes import FINDING_CODES
from .placement_kit import refuse
from .write_ids import id_texts, port_values

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from fransys_layout.core import Finding as CoreFinding
    from fransys_model.kernel import Id, Model

__all__ = ["kernel_findings"]

_BY_CODE = {info.code: info for info in (*LAYOUT_CODES, *FINDING_CODES)}


def _subjects(
    known: Mapping[str, Id[object]], text: str | None
) -> tuple[tuple[Id[object], ...], tuple[str, ...]]:
    """The records a core subject names, and the tokens that name none.

    A block or pair text may name no record at all (a band, a column); only a text that names
    some and not others has a token worth telling the reader about.
    """
    if not text:
        return (), ()
    tokens = [token.strip() for token in text.split(",")]
    heads = [token.partition(".")[0] for token in tokens]
    mapped = tuple(known[h] for h in heads if h in known)
    return mapped, tuple(t for t, h in zip(tokens, heads, strict=True) if mapped and h not in known)


def _message(text: str, unmapped: tuple[str, ...]) -> str:
    return f"{text} (subject not a model record: {', '.join(unmapped)})" if unmapped else text


def kernel_findings(model: Model, findings: Iterable[CoreFinding]) -> tuple[KernelFinding, ...]:
    """One kernel `Finding` per core finding, in order; an unregistered code is refused."""
    known = {**port_values(model), **id_texts(model)}
    out = []
    for found in findings:
        info = _BY_CODE.get(found.code)
        if info is None:
            refuse(
                f"finding code {found.code}",
                "register the code in fransys_el.FINDING_CODES before the core emits it",
            )
        subjects, unmapped = _subjects(known, found.subject)
        out.append(
            KernelFinding(  # the code is registry-checked above, so it has its CodeInfo
                code=found.code,
                severity=info.severities[0],
                subjects=subjects,
                message=_message(found.text, unmapped),
                fix=info.filled(),
            )
        )
    return tuple(out)
