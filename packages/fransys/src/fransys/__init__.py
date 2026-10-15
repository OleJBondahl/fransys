"""Fransys facade: pipeline, findings policy, file writing.

The CLI is deferred (F10).
"""

import importlib.metadata

from fransys_author import AuthorError
from fransys_author.surface import (
    ABOVE,
    AC_CONTROL,
    AC_L1,
    AC_L2,
    AC_L3,
    AC_N,
    AI,
    AO,
    BELOW,
    CONTROL,
    DC_CONTROL,
    DC_GROUND,
    DC_SUPPLY,
    DI,
    DO,
    EARTHED,
    GENERIC,
    IT,
    SIGNAL,
    Design,
    Detail,
    Device,
    Fn,
    Layout,
    Pin,
    Run,
    Terminal,
    TerminalStrip,
    TypedDevice,
    TypedFn,
    unit,
)
from fransys_parts import PartLibraryError

from fransys import derive
from fransys_model.kernel import Draft, Finding, FreezeError, MergeConflict, Model, Severity
from fransys_model.vocab import DocumentPreset, PageKind, SignalType

from ._release_reader import Release, ReleasePin, releases
from ._report import report
from .design import design
from .documents import document
from .parts_module import parts_module
from .pipeline import (
    BuildErrors,
    BuildResult,
    build,
    check,
    diff,
    export_names,
    lint,
    parts,
    release,
    verify,
    write,
)
from .readability import readability

__version__ = importlib.metadata.version("fransys")

__all__ = [
    "ABOVE",
    "AC_CONTROL",
    "AC_L1",
    "AC_L2",
    "AC_L3",
    "AC_N",
    "AI",
    "AO",
    "BELOW",
    "CONTROL",
    "DC_CONTROL",
    "DC_GROUND",
    "DC_SUPPLY",
    "DI",
    "DO",
    "EARTHED",
    "GENERIC",
    "IT",
    "SIGNAL",
    "AuthorError",
    "BuildErrors",
    "BuildResult",
    "Design",
    "Detail",
    "Device",
    "DocumentPreset",
    "Draft",
    "Finding",
    "Fn",
    "FreezeError",
    "Layout",
    "MergeConflict",
    "Model",
    "PageKind",
    "PartLibraryError",
    "Pin",
    "Release",
    "ReleasePin",
    "Run",
    "Severity",
    "SignalType",
    "Terminal",
    "TerminalStrip",
    "TypedDevice",
    "TypedFn",
    "build",
    "check",
    "derive",
    "design",
    "diff",
    "document",
    "export_names",
    "lint",
    "parts",
    "parts_module",
    "readability",
    "release",
    "releases",
    "report",
    "unit",
    "verify",
    "write",
]
