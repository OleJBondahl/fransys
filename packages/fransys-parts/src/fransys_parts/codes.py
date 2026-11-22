"""Part-file finding codes (BUILD-MESSAGES M1): the registry is `codes.toml`, one `[[code]]` table per code."""

import tomllib
from importlib.resources import files

from fransys_model.kernel import CodeBook, CodeInfo, Severity
from fransys_model.vocab import FINDING_CODES as MODEL_CODES

_ROWS = tomllib.loads(files("fransys_parts").joinpath("codes.toml").read_text(encoding="utf-8"))["code"]
FINDING_CODES: tuple[CodeInfo, ...] = tuple(
    CodeInfo(code=r["code"], severity=Severity[r["severity"]], stage=r["stage"], who=r["who"], cause=r["cause"], fix=r["fix"], page=r["page"])
    for r in _ROWS
)

# `lint.py` raises one model code (CABLE_WITHOUT_PRODUCT)
finding = CodeBook(*MODEL_CODES, *FINDING_CODES).finding
