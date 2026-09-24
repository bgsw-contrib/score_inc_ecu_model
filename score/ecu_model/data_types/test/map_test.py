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

import unittest

from pydantic import ValidationError

from score.ecu_model.data_types.common import DataTypeKind, DataTypeSource
from score.ecu_model.data_types.map import MapDataType
from score.ecu_model.data_types.primitives import PrimitiveDataType
from score.ecu_model.data_types.struct import StructDataType


class TestMapDataType(unittest.TestCase):
    def test_creates_map_data_type(self) -> None:
        map_type = MapDataType(
            name="StringToIntMap",
            source_kind=DataTypeSource.FRANCA,
            key_type=PrimitiveDataType.STRING,
            value_type=PrimitiveDataType.INT32,
        )

        self.assertEqual(map_type.kind, DataTypeKind.MAP)
        self.assertEqual(str(map_type.name), "StringToIntMap")
        self.assertFalse(map_type.is_inline)
        self.assertEqual(map_type.key_type, PrimitiveDataType.STRING)
        self.assertEqual(map_type.value_type, PrimitiveDataType.INT32)

    def test_creates_inline_map_without_identifier(self) -> None:
        map_type = MapDataType(
            source_kind=DataTypeSource.PROTOBUF,
            key_type=PrimitiveDataType.STRING,
            value_type=PrimitiveDataType.INT32,
            is_inline=True,
        )

        self.assertIsNone(map_type.name)
        self.assertTrue(map_type.is_inline)
        self.assertEqual(map_type.key_type, PrimitiveDataType.STRING)
        self.assertEqual(map_type.value_type, PrimitiveDataType.INT32)
        with self.assertRaisesRegex(ValueError, "Data types without an identifier do not have a fully qualified name"):
            _ = map_type.fully_qualified_name

    def test_rejects_inline_map_with_identifier(self) -> None:
        with self.assertRaises(ValidationError) as context:
            MapDataType(
                name="BadInline",
                source_kind=DataTypeSource.FRANCA,
                key_type=PrimitiveDataType.STRING,
                value_type=PrimitiveDataType.INT32,
                is_inline=True,
            )
        self.assertIn("inline maps must not have an identifier", str(context.exception))

    def test_rejects_non_inline_map_without_identifier(self) -> None:
        with self.assertRaises(ValidationError) as context:
            MapDataType(
                source_kind=DataTypeSource.FRANCA,
                key_type=PrimitiveDataType.STRING,
                value_type=PrimitiveDataType.INT32,
            )
        self.assertIn("non-inline maps require an identifier", str(context.exception))

    def test_supports_declared_type_ref_as_key_or_value_type(self) -> None:
        value_struct = StructDataType(name="Payload", source_kind=DataTypeSource.FRANCA)
        map_type = MapDataType(
            name="PayloadMap",
            source_kind=DataTypeSource.FRANCA,
            key_type=PrimitiveDataType.STRING,
            value_type=value_struct,
        )

        self.assertIs(map_type.value_type, value_struct)


if __name__ == "__main__":
    unittest.main()
