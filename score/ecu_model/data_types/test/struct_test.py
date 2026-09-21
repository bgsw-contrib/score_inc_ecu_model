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

from score.ecu_model.data_types.common import DataTypeKind, DataTypeSource
from score.ecu_model.data_types.composite import DataTypeField
from score.ecu_model.data_types.enum import EnumDataType
from score.ecu_model.data_types.primitives import PrimitiveDataType
from score.ecu_model.data_types.struct import StructDataType


class TestStructDataType(unittest.TestCase):
    @staticmethod
    def _field(
        identifier: str,
        data_type: object = PrimitiveDataType.UINT32,
        field_number: int | None = None,
    ) -> DataTypeField:
        return DataTypeField(name=identifier, data_type=data_type, field_number=field_number)

    def test_keeps_declared_fields_in_order(self) -> None:
        data_type = StructDataType(
            name="Position",
            source_kind=DataTypeSource.PROTOBUF,
            fields=[self._field("x", field_number=1), self._field("y", field_number=2)],
        )

        self.assertEqual(data_type.kind, DataTypeKind.STRUCT)
        self.assertIsInstance(data_type.fields, tuple)
        self.assertEqual(str(data_type.fields[0].name), "x")
        self.assertEqual(str(data_type.fields[1].name), "y")

    def test_defaults_to_a_required_field_without_wire_tag(self) -> None:
        field = DataTypeField(name="x", data_type=PrimitiveDataType.UINT32)

        self.assertIsNone(field.field_number)
        self.assertFalse(field.optional)
        self.assertEqual(field.deployment_properties, {})

    def test_supports_declared_data_types_as_field_type(self) -> None:
        nested = StructDataType(name="Position", source_kind=DataTypeSource.FRANCA)
        data_type = StructDataType(
            name="Pose",
            source_kind=DataTypeSource.FRANCA,
            fields=[self._field("position", nested)],
        )

        self.assertIs(data_type.fields[0].data_type, nested)

    def test_keeps_directly_nested_structs_and_enums(self) -> None:
        nested_struct = StructDataType(name="Sample", source_kind=DataTypeSource.PROTOBUF)
        nested_enum = EnumDataType(name="State", source_kind=DataTypeSource.PROTOBUF)
        data_type = StructDataType(
            name="Envelope",
            source_kind=DataTypeSource.PROTOBUF,
            nested_enums=[nested_enum],
            nested_structs=[nested_struct],
        )

        self.assertIsInstance(data_type.nested_enums, tuple)
        self.assertIsInstance(data_type.nested_structs, tuple)
        self.assertIs(data_type.nested_enums[0], nested_enum)
        self.assertIs(data_type.nested_structs[0], nested_struct)

    def test_prevents_in_place_field_mutation(self) -> None:
        data_type = StructDataType(
            name="Position",
            source_kind=DataTypeSource.FRANCA,
            fields=[self._field("x")],
        )

        with self.assertRaises(AttributeError):
            data_type.fields.append(self._field("y"))  # type: ignore[attr-defined]


if __name__ == "__main__":
    unittest.main()
