"""Fransys facade: pipeline, findings policy, file writing.

Documentation: https://olejbondahl.github.io/fransys/ (the site is the official copy,
not the installed files). Look a name or a finding code up with `python -m fransys help KEY`.
"""

from typing import NoReturn

from fransys_author import AuthorError
from fransys_author.surface import (
    AC_CONTROL,
    AC_L1,
    AC_L2,
    AC_L3,
    AC_N,
    AI,
    AO,
    CONTROL,
    DC_CONTROL,
    DC_GROUND,
    DC_SIGNAL,
    DC_SUPPLY,
    DI,
    DO,
    GENERIC,
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
    refuse,
    unit,
)
from fransys_parts import PartLibraryError

from fransys import derive
from fransys_model import elecdef
from fransys_model.derive.docs_site import version_url
from fransys_model.kernel import Draft, Finding, FreezeError, MergeConflictError, Model, Severity
from fransys_model.vocab import DocumentPreset, PageKind, SignalType

from ._exports import export_names, write
from ._release_cmds import diff, rebaseline, release, verify
from ._release_reader import Release, ReleasePin, releases
from ._report import report
from ._version import __version__
from .design import design
from .documents import document
from .errors import FransysError
from .parts_module import parts_module
from .pipeline import BuildFailedError, BuildResult, build, check, lint, parts
from .readability import readability
from .settings import Settings, SettingsError, settings

__doc__ += f"\nThis install, {__version__}: {version_url(__version__)} (agents: {version_url(__version__)}llms.txt)."


def __getattr__(name: str) -> NoReturn:
    """Refuse a missing name of `fr`: a removed one names its new spelling (deleted at the 0.23 tag)."""
    refuse("fr", name)


__all__ = [
    "AC_CONTROL",
    "AC_L1",
    "AC_L2",
    "AC_L3",
    "AC_N",
    "AI",
    "AO",
    "CONTROL",
    "DC_CONTROL",
    "DC_GROUND",
    "DC_SIGNAL",
    "DC_SUPPLY",
    "DI",
    "DO",
    "GENERIC",
    "SIGNAL",
    "AcSupply",
    "AuthorError",
    "BuildFailedError",
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
    "FransysError",
    "FreezeError",
    "Layout",
    "MergeConflictError",
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
    "elecdef",
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
