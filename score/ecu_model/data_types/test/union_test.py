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
from score.ecu_model.data_types.composite import DataTypeField
from score.ecu_model.data_types.primitives import PrimitiveDataType
from score.ecu_model.data_types.union import UnionDataType


class TestUnionDataType(unittest.TestCase):
    @staticmethod
    def _field(
        identifier: str,
        data_type: object = PrimitiveDataType.UINT32,
        field_number: int | None = None,
        optional: bool = False,
    ) -> DataTypeField:
        return DataTypeField(
            name=identifier,
            data_type=data_type,
            field_number=field_number,
            optional=optional,
        )

    def test_keeps_declared_fields_in_order(self) -> None:
        data_type = UnionDataType(
            name="Measurement",
            source_kind=DataTypeSource.PROTOBUF,
            fields=[self._field("distance", field_number=1), self._field("angle", field_number=2)],
        )

        self.assertEqual(data_type.kind, DataTypeKind.UNION)
        self.assertIsInstance(data_type.fields, tuple)
        self.assertEqual(str(data_type.fields[0].name), "distance")
        self.assertEqual(str(data_type.fields[1].name), "angle")

    def test_rejects_optional_fields(self) -> None:
        with self.assertRaisesRegex(ValidationError, "union fields must not be declared optional"):
            UnionDataType(
                name="Measurement",
                source_kind=DataTypeSource.FRANCA,
                fields=[self._field("distance", optional=True)],
            )


if __name__ == "__main__":
    unittest.main()
