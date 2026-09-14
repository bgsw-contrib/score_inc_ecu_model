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
from score.ecu_model.data_types.struct import StructDataType


class TestProtobufValidation(unittest.TestCase):
    def test_protobuf_identifier_and_package_are_validated(self) -> None:
        StructDataType(
            kind=DataTypeKind.STRUCT,
            name="MyMessage",
            namespace="com.example.sensor",
            source_kind=DataTypeSource.PROTOBUF,
        )

        with self.assertRaises(ValueError):
            StructDataType(
                kind=DataTypeKind.STRUCT,
                name="1invalid",
                source_kind=DataTypeSource.PROTOBUF,
            )

        with self.assertRaises(ValueError):
            StructDataType(
                kind=DataTypeKind.STRUCT,
                name="MyMessage",
                namespace="com..example",
                source_kind=DataTypeSource.PROTOBUF,
            )

    def test_protobuf_fully_qualified_name(self) -> None:
        dt1 = StructDataType(
            kind=DataTypeKind.STRUCT,
            name="MyMessage",
            namespace="com.example.sensor",
            source_kind=DataTypeSource.PROTOBUF,
        )
        self.assertEqual(dt1.fully_qualified_name, "com.example.sensor.MyMessage")

        dt2 = StructDataType(
            kind=DataTypeKind.STRUCT,
            name="MyMessage",
            source_kind=DataTypeSource.PROTOBUF,
        )
        self.assertEqual(dt2.fully_qualified_name, "MyMessage")


if __name__ == "__main__":
    unittest.main()
