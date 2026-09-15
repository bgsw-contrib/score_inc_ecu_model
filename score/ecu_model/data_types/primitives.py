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

from enum import Enum


class PrimitiveDataType(str, Enum):
    """
    Canonical primitive data types supported by generator inputs, compilers, and other tools.
    Everything that is expected to be available without an explicit declaration in the source model.
    """

    STRING = "string"
    BYTES = "bytes"
    BOOL = "bool"
    DOUBLE = "double"
    FLOAT = "float"
    UINT8 = "uint8"
    UINT16 = "uint16"
    UINT32 = "uint32"
    UINT64 = "uint64"
    INT8 = "int8"
    INT16 = "int16"
    INT32 = "int32"
    INT64 = "int64"

    def __str__(self) -> str:
        return self.value
