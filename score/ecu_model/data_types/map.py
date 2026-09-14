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

from typing import Literal

from pydantic import Field

from score.ecu_model.data_types.common import DataTypeBase, DataTypeKind, DataTypeOrReference


class MapDataType(DataTypeBase):
    """Definition of a map data type with key and value types."""

    kind: Literal[DataTypeKind.MAP] = Field(default=DataTypeKind.MAP, frozen=True)
    key_type: DataTypeOrReference = Field(
        description="Map key type definition; may temporarily be an unresolved reference during model resolution",
    )
    value_type: DataTypeOrReference = Field(
        description="Map value type definition; may temporarily be an unresolved reference during model resolution",
    )
