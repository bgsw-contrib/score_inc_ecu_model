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

"""Public Protobuf parser API for pipeline ingestion."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from score.parsers.protobuf_parser.transformer import (
    DescriptorSetTransformer,
)
from score.parsers.protobuf_parser.resolver import (
    ProtoResolverError,
    resolve_references,
)
from score.ecu_model.data_types.common import DataTypeBase


class ProtobufToDataTypeParser:
    """Parse Protobuf descriptor artifacts into a mutable, resolved mapping."""

    @staticmethod
    def parse(
        descriptor_set_paths: Iterable[str | Path],
    ) -> dict[str, DataTypeBase]:
        """Load, parse, and resolve protoc-produced descriptor artifacts by data type key."""
        transformed_result = DescriptorSetTransformer(descriptor_set_paths).transform()
        definitions_by_key = transformed_result.definitions_by_key

        protobuf_resolution_issues = resolve_references(transformed_result.unresolved_references, definitions_by_key)
        if protobuf_resolution_issues:
            message = "; ".join(f"{issue.code}: {issue.message}" for issue in protobuf_resolution_issues)
            raise ProtoResolverError(message)

        return definitions_by_key
