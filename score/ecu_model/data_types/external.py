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
from __future__ import annotations

from re import fullmatch
from typing import Literal

from pydantic import Field, field_validator

from score.ecu_model.data_types.common import DataTypeBase, DataTypeKind, DataTypeSource


class ExternalDataType(DataTypeBase):
    """Definition of a type provided by an existing C++ header without modeled internals."""

    kind: Literal[DataTypeKind.EXTERNAL] = Field(default=DataTypeKind.EXTERNAL, frozen=True)
    source_kind: DataTypeSource = Field(
        default=DataTypeSource.CPP_HEADER_FILE,
        description="Origin of the data type definition, defaults to CPP_HEADER_FILE for external types",
    )
    header: str = Field(
        description="Header include path or explicitly quoted/bracketed include",
    )
    bazel_target: str | None = Field(
        default=None,
        description="Optional Bazel dependency target providing the header",
    )

    @field_validator("bazel_target")
    @classmethod
    def _validate_bazel_target(cls, value: str | None) -> str | None:
        """Validate the optional Bazel label that supplies the header."""
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("bazel_target must not be empty when provided")
        if "\x00" in stripped:
            raise ValueError("bazel_target must not contain null bytes")
        absolute_label_pattern = (
            r"(?:@[A-Za-z0-9._+-]+)?//(?:[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*)?(?::[A-Za-z0-9._+-]+)?"
        )
        relative_label_pattern = r":[A-Za-z0-9._+-]+"
        if not fullmatch(f"(?:{absolute_label_pattern}|{relative_label_pattern})", stripped):
            raise ValueError("bazel_target must be a valid Bazel label")
        return stripped
