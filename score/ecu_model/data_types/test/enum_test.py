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
from score.ecu_model.data_types.enum import EnumDataType, EnumValue
from score.ecu_model.data_types.primitives import PrimitiveDataType
from score.ecu_model.data_types.struct import StructDataType


class TestEnumDataType(unittest.TestCase):
    @staticmethod
    def _value(identifier: str, value: int | None = None) -> EnumValue:
        return EnumValue(name=identifier, value=value)

    def test_defaults_to_uint32_and_keeps_declared_literals(self) -> None:
        data_type = EnumDataType(
            name="Gear",
            source_kind=DataTypeSource.FRANCA,
            values=[self._value("PARK", 0), self._value("DRIVE", 1)],
        )

        self.assertEqual(data_type.kind, DataTypeKind.ENUM)
        self.assertEqual(data_type.underlying_type, PrimitiveDataType.UINT32)
        self.assertIsInstance(data_type.values, tuple)
        self.assertEqual(str(data_type.values[0].name), "PARK")
        self.assertEqual(data_type.values[0].value, 0)
        self.assertEqual(str(data_type.values[1].name), "DRIVE")
        self.assertEqual(data_type.values[1].value, 1)

    def test_allows_literal_value_assignment(self) -> None:
        data_type = EnumDataType(
            name="Gear",
            source_kind=DataTypeSource.FRANCA,
            values=[self._value("PARK", 0)],
        )

        with self.assertRaises(AttributeError):
            data_type.values.append(self._value("DRIVE", 1))  # type: ignore[attr-defined]
        data_type.values[0].value = 1
        self.assertEqual(data_type.values[0].value, 1)

    def test_reassignment_validates_literal_value_definitions(self) -> None:
        data_type = EnumDataType(
            name="Gear",
            source_kind=DataTypeSource.FRANCA,
            values=[self._value("PARK", 0)],
        )

        with self.assertRaisesRegex(
            ValidationError, "enum values must either all be explicitly defined or all be omitted"
        ):
            data_type.values = (self._value("PARK", 0), self._value("DRIVE"))

    def test_rejects_mixed_explicit_and_implicit_literal_values(self) -> None:
        with self.assertRaisesRegex(
            ValidationError, "enum values must either all be explicitly defined or all be omitted"
        ):
            EnumDataType(
                name="Gear",
                source_kind=DataTypeSource.FRANCA,
                values=[self._value("PARK", 0), self._value("DRIVE")],
            )

    def test_rejects_duplicate_literal_identifiers(self) -> None:
        with self.assertRaisesRegex(ValidationError, "enum value identifiers must be unique"):
            EnumDataType(
                name="Gear",
                source_kind=DataTypeSource.FRANCA,
                values=[self._value("PARK", 0), self._value("PARK", 1)],
            )

    def test_rejects_duplicate_explicit_literal_values(self) -> None:
        with self.assertRaisesRegex(ValidationError, "explicit enum values must be unique"):
            EnumDataType(
                name="Gear",
                source_kind=DataTypeSource.FRANCA,
                values=[self._value("PARK", 0), self._value("DRIVE", 0)],
            )

    def test_supports_extending_another_declared_enum(self) -> None:
        parent = EnumDataType(name="BaseGear", source_kind=DataTypeSource.FRANCA)
        child = EnumDataType(
            name="Gear",
            source_kind=DataTypeSource.FRANCA,
            extends=parent,
        )

        self.assertIs(child.extends, parent)

    def test_rejects_extending_base_type_of_different_kind(self) -> None:
        parent_struct = StructDataType(name="BaseStruct", source_kind=DataTypeSource.FRANCA)

        with self.assertRaises(ValidationError):
            EnumDataType(
                name="ChildEnum",
                source_kind=DataTypeSource.FRANCA,
                extends=parent_struct,
            )

    def test_rejects_boolean_literal_values(self) -> None:
        with self.assertRaises(ValidationError):
            EnumValue(name="PARK", value=True)

    def test_accepts_negative_literal_values(self) -> None:
        data_type = EnumDataType(
            name="Gear",
            source_kind=DataTypeSource.FRANCA,
            values=[self._value("REVERSE", -1), self._value("PARK", 0)],
        )

        self.assertEqual(data_type.values[0].value, -1)

    def test_rejects_literal_identifier_invalid_for_source_language(self) -> None:
        with self.assertRaisesRegex(ValidationError, "Invalid identifier '1PARK'"):
            EnumDataType(
                name="Gear",
                source_kind=DataTypeSource.FRANCA,
                values=[self._value("1PARK")],
            )


if __name__ == "__main__":
    unittest.main()
