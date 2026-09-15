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

from score.ecu_model.data_types.array import ArrayDataType
from score.ecu_model.data_types.common import DataTypeSource
from score.ecu_model.data_types.composite import DataTypeField
from score.ecu_model.data_types.enum import EnumDataType
from score.ecu_model.data_types.identifier import Identifier
from score.ecu_model.data_types.map import MapDataType
from score.ecu_model.data_types.primitives import PrimitiveDataType
from score.ecu_model.data_types.struct import StructDataType
from score.ecu_model.data_types.typedef import TypedefDataType


class TestUnresolvedDataTypeReference(unittest.TestCase):
    @staticmethod
    def _qualified_reference() -> Identifier:
        return Identifier("Position")

    def test_typedef_accepts_unqualified_reference(self) -> None:
        reference = Identifier("Position")

        typedef = TypedefDataType(
            name="PositionAlias",
            source_kind=DataTypeSource.FRANCA,
            data_type=reference,
        )

        self.assertIs(typedef.data_type, reference)

    def test_typedef_accepts_qualified_reference(self) -> None:
        reference = self._qualified_reference()

        typedef = TypedefDataType(
            name="PositionAlias",
            source_kind=DataTypeSource.FRANCA,
            data_type=reference,
        )

        self.assertIs(typedef.data_type, reference)

    def test_reference_is_replaceable_by_the_resolved_data_type(self) -> None:
        typedef = TypedefDataType(
            name="PositionAlias",
            source_kind=DataTypeSource.FRANCA,
            data_type=self._qualified_reference(),
        )
        resolved = StructDataType(name="Position", source_kind=DataTypeSource.FRANCA)

        typedef.data_type = resolved

        self.assertIs(typedef.data_type, resolved)

    def test_map_accepts_references_as_key_and_value_type(self) -> None:
        key_reference = Identifier("Key")
        value_reference = self._qualified_reference()

        map_type = MapDataType(
            name="PositionsByKey",
            source_kind=DataTypeSource.FRANCA,
            key_type=key_reference,
            value_type=value_reference,
        )

        self.assertIs(map_type.key_type, key_reference)
        self.assertIs(map_type.value_type, value_reference)

    def test_array_accepts_reference_as_element_type(self) -> None:
        reference = self._qualified_reference()

        array = ArrayDataType(
            name="Positions",
            source_kind=DataTypeSource.FRANCA,
            data_type=reference,
        )

        self.assertIs(array.data_type, reference)

    def test_field_accepts_reference_as_data_type(self) -> None:
        reference = self._qualified_reference()

        field = DataTypeField(name="position", data_type=reference)

        self.assertIs(field.data_type, reference)

    def test_struct_accepts_reference_as_base_type(self) -> None:
        reference = self._qualified_reference()

        struct = StructDataType(
            name="ExtendedPosition",
            source_kind=DataTypeSource.FRANCA,
            extends=reference,
        )

        self.assertIs(struct.extends, reference)

    def test_enum_accepts_reference_as_base_type(self) -> None:
        reference = self._qualified_reference()

        enum = EnumDataType(
            name="ExtendedSeverity",
            source_kind=DataTypeSource.FRANCA,
            extends=reference,
        )

        self.assertIs(enum.extends, reference)

    def test_rejects_reference_as_base_type_for_non_franca_source(self) -> None:
        with self.assertRaisesRegex(
            ValidationError, "StructDataType inheritance is only allowed for FRANCA source kind"
        ):
            StructDataType(
                name="ExtendedPosition",
                source_kind=DataTypeSource.PROTOBUF,
                extends=self._qualified_reference(),
            )

    def test_interprets_a_plain_string_as_an_unresolved_reference(self) -> None:
        typedef = TypedefDataType(
            name="Counter",
            source_kind=DataTypeSource.FRANCA,
            data_type="uint32",
        )

        self.assertEqual(typedef.data_type, Identifier("uint32"))

    def test_keeps_a_primitive_passed_as_enum_member(self) -> None:
        typedef = TypedefDataType(
            name="Counter",
            source_kind=DataTypeSource.FRANCA,
            data_type=PrimitiveDataType.UINT32,
        )

        self.assertEqual(typedef.data_type, PrimitiveDataType.UINT32)


if __name__ == "__main__":
    unittest.main()
