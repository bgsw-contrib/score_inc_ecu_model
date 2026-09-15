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


class TestCppValidation(unittest.TestCase):
    def test_cpp_identifier_and_namespace_are_validated(self) -> None:
        StructDataType(
            kind=DataTypeKind.STRUCT,
            name="_value2",
            namespace="app::geometry",
            source_kind=DataTypeSource.CPP_HEADER_FILE,
        )

        with self.assertRaises(ValueError):
            StructDataType(
                kind=DataTypeKind.STRUCT,
                name="with-dash",
                source_kind=DataTypeSource.CPP_HEADER_FILE,
            )

        with self.assertRaises(ValueError):
            StructDataType(
                kind=DataTypeKind.STRUCT,
                name="Position",
                namespace="app::geometry::",
                source_kind=DataTypeSource.CPP_HEADER_FILE,
            )

    def test_cpp_fully_qualified_name(self) -> None:
        dt1 = StructDataType(
            kind=DataTypeKind.STRUCT,
            name="Vector3D",
            namespace="app::geometry",
            source_kind=DataTypeSource.CPP_HEADER_FILE,
        )
        self.assertEqual(dt1.fully_qualified_name, "app::geometry::Vector3D")

        dt2 = StructDataType(
            kind=DataTypeKind.STRUCT,
            name="Vector3D",
            source_kind=DataTypeSource.CPP_HEADER_FILE,
        )
        self.assertEqual(dt2.fully_qualified_name, "Vector3D")


if __name__ == "__main__":
    unittest.main()
