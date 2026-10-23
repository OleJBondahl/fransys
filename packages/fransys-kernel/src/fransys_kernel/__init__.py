"""Generic layer: records, ids, freeze, canonical form, merge. Knows nothing about engineering."""

from .cache import DIGEST_CACHE_SIZE, ByDigest, digest_cached
from .canonical_forms import dumps, from_data, loads, to_data
from .codes import WHO_ACTS, CodeInfo
from .diff import ModelDiff, diff
from .draft import Draft
from .encode import JsonValue, decimal_text, write_json
from .errors import (
    FreezeError,
    MergeConflict,
    ModelError,
    RefError,
    SchemaError,
    SchemaVersionError,
    ValueTypeError,
)
from .evolve import evolve
from .findings import Finding, Severity
from .freeze import freeze
from .grouping import index_ids
from .ids import AuthoringKey, Id, make_id, render_id
from .jsonread import read_json
from .merge import merge
from .model import Model
from .naturals import NaturalKey, canonical, natural_join, natural_key, natural_sorted
from .origin import DescribedFinding, Origin, OriginSource, describe, describe_parts, require_origin
from .parents import parent_chain
from .record import FieldSpec, field_specs, record, value
from .record_protocol import Record, key_text
from .registry import (
    lookup_kind,
    namespace_of,
    register_kind,
    register_namespaces,
    register_schema_version,
)
from .unionfind import UnionFind
from .values import Value, check_value, register_enum

__all__ = [
    "DIGEST_CACHE_SIZE",
    "WHO_ACTS",
    "AuthoringKey",
    "ByDigest",
    "CodeInfo",
    "DescribedFinding",
    "Draft",
    "FieldSpec",
    "Finding",
    "FreezeError",
    "Id",
    "JsonValue",
    "MergeConflict",
    "Model",
    "ModelDiff",
    "ModelError",
    "NaturalKey",
    "Origin",
    "OriginSource",
    "Record",
    "RefError",
    "SchemaError",
    "SchemaVersionError",
    "Severity",
    "UnionFind",
    "Value",
    "ValueTypeError",
    "canonical",
    "check_value",
    "decimal_text",
    "describe",
    "describe_parts",
    "diff",
    "digest_cached",
    "dumps",
    "evolve",
    "field_specs",
    "freeze",
    "from_data",
    "index_ids",
    "key_text",
    "loads",
    "lookup_kind",
    "make_id",
    "merge",
    "namespace_of",
    "natural_join",
    "natural_key",
    "natural_sorted",
    "parent_chain",
    "read_json",
    "record",
    "register_enum",
    "register_kind",
    "register_namespaces",
    "register_schema_version",
    "render_id",
    "require_origin",
    "to_data",
    "value",
    "write_json",
]
