"""The one map from a core `Finding` to the kernel's (P6.1 D; DRAWING-VALUE reads it too).

The code's severity and fix come from `fransys_el.FINDING_CODES` and `fransys_layout.FINDING_CODES`;
the core carries only text.
"""

import re
from typing import TYPE_CHECKING, cast

from fransys_layout import FINDING_CODES as LAYOUT_CODES
lazy from fransys_model.derive import tag_text, unit_label
lazy from fransys_model.kernel import Finding as KernelFinding

from .codes import FINDING_CODES
from .placement_kit import refuse
from .placement_nets import net_ports
from .write_ids import id_texts

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from fransys_layout.core import Finding as CoreFinding
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Function

__all__ = ["kernel_findings"]

_BY_CODE = {info.code: info for info in (*LAYOUT_CODES, *FINDING_CODES)}


def _subjects(known: Mapping[str, Id[object]], text: str | None) -> tuple[tuple[Id[object], ...], tuple[str, ...]]:
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


def _named(model: Model, symbols: Mapping[str, Id[object]], text: str) -> str:
    """`text` with each core symbol key and unit id it prints replaced by its designation or label: a key is internal."""
    names = {k: tag_text(model, cast("Id[Function]", f)) for k, f in symbols.items()}
    names |= {u.value: unit_label(model, u) for u in model.tables.get("unit", {})}
    if not names:
        return text
    keys = re.compile("|".join(re.escape(k) for k in names))
    return keys.sub(lambda m: names[m.group()], text)


def _message(text: str, unmapped: tuple[str, ...]) -> str:
    return f"{text} (subject not a model record: {', '.join(unmapped)})" if unmapped else text


def kernel_findings(model: Model, findings: Iterable[CoreFinding], symbols: Mapping[str, Id[object]]) -> tuple[KernelFinding, ...]:
    """One kernel `Finding` per core finding, in order; an unregistered code is refused.

    `symbols` maps a core symbol id to the function it draws (`symbol_subjects`), so a finding
    on a cell, an annex owner or a box names a record and its fix can print the subject.
    """
    known = {**net_ports(model), **id_texts(model), **symbols}
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
            info.finding(subjects, _message(_named(model, symbols, found.text), unmapped))  # the code is registry-checked above
        )
    return tuple(out)
