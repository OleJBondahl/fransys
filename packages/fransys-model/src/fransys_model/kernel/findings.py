"""Kernel findings.

Reported engineering problems, returned rather than raised (design/kernel-model.md 5.8, decision
0006).
"""

import re
from enum import Enum
from typing import Any

from .errors import SchemaError
from .ids import Id
from .record import value
from .values import register_enum

_CODE = re.compile(r"[A-Z][A-Z0-9_]*")


@register_enum
class Severity(Enum):
    """How much a `Finding` should block a downstream output.

    Fransys, not this repo, decides which severities block which outputs.

    Attributes:
        INFO: Worth noting; blocks nothing in the facade's own policy.
        WARNING: Worth a look; also blocks nothing in the facade's own policy.
        ERROR: Blocks every export: the facade's `write` raises and writes nothing while
            any `Finding` of this severity remains.
    """

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@value
class Finding:
    """One reported engineering problem: one shape for every domain validator.

    `code` is a stable `UPPER_SNAKE` string (e.g. `NET_UNREALISED`), listed in the module
    that emits it. `subjects` names the ids the finding is about, stored in `Id` order so
    that neither the order a validator happened to find them in nor a repeat matters.

    Attributes:
        code: A stable `UPPER_SNAKE` string identifying the kind of problem (e.g.
            `NET_UNREALISED`), listed in the module that emits it.
        severity: How much this finding should block a downstream output.
        subjects: The ids this finding is about, stored once each, in `Id` order.
        message: The human-readable text of the finding.
    """

    code: str
    severity: Severity
    subjects: tuple[Id[Any], ...]
    message: str

    def __post_init__(self) -> None:
        """Refuse a malformed `code` or a subject that is not an `Id`; store subjects once each.

        Raises `SchemaError` when `code` is not `UPPER_SNAKE`, or a subject is not an `Id`.
        """
        if _CODE.fullmatch(self.code) is None:
            msg = f"finding code {self.code!r} is not UPPER_SNAKE"
            raise SchemaError(msg, kind=type(self).__qualname__)
        if not all(isinstance(subject, Id) for subject in self.subjects):
            msg = "every finding subject must be an Id"
            raise SchemaError(msg, kind=type(self).__qualname__)
        object.__setattr__(self, "subjects", tuple(sorted(set(self.subjects))))
