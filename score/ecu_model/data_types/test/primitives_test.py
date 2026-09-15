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

from score.ecu_model.data_types.primitives import PrimitiveDataType


class TestPrimitiveDataType(unittest.TestCase):
    def test_value_is_canonical_name(self) -> None:
        self.assertEqual(PrimitiveDataType.UINT32.value, "uint32")
        self.assertEqual(str(PrimitiveDataType.UINT32), "uint32")

    def test_parsed_from_canonical_name(self) -> None:
        self.assertIs(PrimitiveDataType("uint32"), PrimitiveDataType.UINT32)

    def test_unknown_name_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            PrimitiveDataType("uint24")


if __name__ == "__main__":
    unittest.main()
