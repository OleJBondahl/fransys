"""Fransys facade: pipeline, findings policy, file writing.

Documentation: https://olejbondahl.github.io/fransys/ (the site is the official copy,
not the installed files). Look a name or a finding code up with `python -m fransys help KEY`.
"""

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
    DC_SIGNAL,
    DC_SUPPLY,
    DI,
    DO,
    EARTHED,
    GENERIC,
    IT,
    SIGNAL,
    AcSupply,
    Cable,
    DcSupply,
    Design,
    Detail,
    Device,
    Fn,
    Layout,
    Pin,
    Run,
    SupplyRail,
    Terminal,
    TerminalStrip,
    Throw,
    TypedDevice,
    TypedFn,
    UnitDef,
    unit,
)
from fransys_parts import PartLibraryError

from fransys import derive
from fransys_model.derive.docs_site import version_url
from fransys_model.kernel import Draft, Finding, FreezeError, MergeConflict, Model, Severity
from fransys_model.vocab import DocumentPreset, PageKind, SignalType

from ._release_reader import Release, ReleasePin, releases
from ._report import report
from ._version import __version__
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
    rebaseline,
    release,
    verify,
    write,
)
from .readability import readability
from .settings import Settings, SettingsError, settings

__doc__ += (
    f"\nThis install, {__version__}: {version_url(__version__)}"
    f" (agents: {version_url(__version__)}llms.txt)."
)

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
    "DC_SIGNAL",
    "DC_SUPPLY",
    "DI",
    "DO",
    "EARTHED",
    "GENERIC",
    "IT",
    "SIGNAL",
    "AcSupply",
    "AuthorError",
    "BuildErrors",
    "BuildResult",
    "Cable",
    "DcSupply",
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
    "Settings",
    "SettingsError",
    "Severity",
    "SignalType",
    "SupplyRail",
    "Terminal",
    "TerminalStrip",
    "Throw",
    "TypedDevice",
    "TypedFn",
    "UnitDef",
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
    "rebaseline",
    "release",
    "releases",
    "report",
    "settings",
    "unit",
    "verify",
    "write",
]
