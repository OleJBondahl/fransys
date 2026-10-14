"""Fransys facade: pipeline, findings policy, file writing.

The CLI is deferred (F10).
"""

import importlib.metadata

from fransys_author import AuthorError
from fransys_author.surface import (
    ABOVE,
    AI,
    AO,
    BELOW,
    CONTROL,
    DI,
    DO,
    EARTHED,
    GENERIC,
    IT,
    SIGNAL,
    Design,
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
from fransys_model.vocab import DocumentPreset, PageKind

from ._release_reader import Release, ReleasePin, releases
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
    "AI",
    "AO",
    "BELOW",
    "CONTROL",
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
    "unit",
    "verify",
    "write",
]
