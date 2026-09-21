# *******************************************************************************
# Copyright (c) 2026 Contributors to the Eclipse Foundation
#
# See the NOTICE file(s) distributed with this work for additional
# information regarding copyright ownership.
#
# This program and the accompanying materials are made available under the
# terms of the Apache License Version 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0
# *******************************************************************************

"""Shared protobuf transformer types, errors, and naming helpers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from score.ecu_model.data_types.common import DataTypeBase
from score.ecu_model.data_types.composite import DataTypeField
from score.ecu_model.data_types.identifier import (
    Identifier,
    QualifiedName,
)


class ProtoTransformerError(ValueError):
    """Raised when descriptor-to-model conversion fails."""


@dataclass(frozen=True)
class SourceSpan:
    """Source location used by transformer and resolver issue reports."""

    file_path: str
    line: int
    column: int = 1


@dataclass(frozen=True)
class ProtoResolverIssue:
    """A structured issue found while resolving a Protobuf reference."""

    phase: str
    code: str
    message: str
    span: SourceSpan


class ReferenceTargetKind(str, Enum):
    """Model locations that may hold a deferred type reference."""

    FIELD_DATA_TYPE = "field_data_type"
    ARRAY_ELEMENT_TYPE = "array_element_type"
    MAP_KEY_TYPE = "map_key_type"
    MAP_VALUE_TYPE = "map_value_type"


@dataclass(frozen=True)
class ReferenceTarget:
    """Direct model target for a deferred reference's destination slot."""

    field: DataTypeField
    owner_definition_key: str
    kind: ReferenceTargetKind


@dataclass(frozen=True)
class UnresolvedReference:
    """A user-defined field type that is unresolved until all definitions are registered."""

    protobuf_type_name: str
    file_path: str
    target: ReferenceTarget


@dataclass
class TransformResult:
    """Deployment definitions and deferred protobuf references."""

    definitions_by_key: dict[str, DataTypeBase]
    unresolved_references: list[UnresolvedReference]


def qualified_name(parts: tuple[str, ...]) -> QualifiedName:
    """Convert protobuf namespace components to a deployment namespace."""
    return QualifiedName(tuple(Identifier(part) for part in parts))


def protobuf_fqn(parts: tuple[str, ...]) -> str:
    """Return a non-empty protobuf fully-qualified name without its leading dot."""
    if not parts:
        raise ProtoTransformerError("A protobuf declaration must have a non-empty name")
    return ".".join(parts)


def package_parts(package: str, file_path: str) -> tuple[str, ...]:
    """Validate and split a protobuf package into namespace components."""
    if not package:
        return ()
    parts = tuple(package.split("."))
    if any(not part for part in parts):
        raise ProtoTransformerError(f"{file_path}: malformed protobuf package '{package}'")
    try:
        qualified_name(parts)
    except ValueError as error:
        raise ProtoTransformerError(f"{file_path}: malformed protobuf package '{package}'") from error
    return parts


def require_name(name: str, *, file_path: str, descriptor_kind: str) -> str:
    """Return a required descriptor name or raise a transformer error."""
    if not name:
        raise ProtoTransformerError(f"{file_path}: {descriptor_kind} has no name")
    return name


def protobuf_reference(raw_name: str, *, file_path: str) -> QualifiedName:
    """Convert a protobuf type name to a deployment-model reference."""
    normalized_name = raw_name.lstrip(".")
    if not normalized_name:
        raise ProtoTransformerError(f"{file_path}: field type has no protobuf type name")
    try:
        return qualified_name(tuple(normalized_name.split(".")))
    except ValueError as error:
        raise ProtoTransformerError(f"{file_path}: malformed protobuf type name '{raw_name}'") from error
