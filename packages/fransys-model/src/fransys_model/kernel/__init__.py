"""Generic layer: records, ids, freeze, canonical form, merge. Knows nothing about engineering."""

from .cache import DIGEST_CACHE_SIZE, ByDigest, digest_cached
from .canonical import dumps, from_data, loads, to_data
from .diff import ModelDiff, diff
from .draft import Draft
from .encode import JsonValue, write_json
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
from .merge import merge
from .model import SCHEMA_VERSION, Model
from .origin import Origin, OriginSource, describe, require_origin
from .parents import parent_chain
from .record import FieldSpec, Record, field_specs, key_text, record, value
from .registry import lookup_kind, namespace_of, register_kind, register_namespaces
from .unionfind import UnionFind
from .values import Value, check_value, register_enum

__all__ = [
    "DIGEST_CACHE_SIZE",
    "SCHEMA_VERSION",
    "AuthoringKey",
    "ByDigest",
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
    "check_value",
    "describe",
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
    "parent_chain",
    "record",
    "register_enum",
    "register_kind",
    "register_namespaces",
    "render_id",
    "require_origin",
    "to_data",
    "value",
    "write_json",
]
