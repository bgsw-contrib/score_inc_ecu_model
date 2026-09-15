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
from score.ecu_model.data_types.external import ExternalDataType


class TestExternalDataType(unittest.TestCase):
    def test_creates_external_data_type(self) -> None:
        data_type = ExternalDataType(
            name="AbortTransfer",
            namespace="adp::managed_data_transfer",
            header="adp/managed_data_transfer/types.h",
        )

        self.assertEqual(data_type.kind, DataTypeKind.EXTERNAL)
        self.assertEqual(data_type.source_kind, DataTypeSource.CPP_HEADER_FILE)
        self.assertEqual(str(data_type.name), "AbortTransfer")
        self.assertEqual(tuple(str(segment) for segment in data_type.namespace), ("adp", "managed_data_transfer"))
        self.assertEqual(data_type.fully_qualified_name, "adp::managed_data_transfer::AbortTransfer")
        self.assertEqual(data_type.header, "adp/managed_data_transfer/types.h")

    def test_keeps_a_bracketed_include_verbatim(self) -> None:
        data_type = ExternalDataType(name="Point", header="<geometry/point.hpp>")

        self.assertEqual(data_type.header, "<geometry/point.hpp>")

    def test_requires_a_header(self) -> None:
        with self.assertRaises(ValidationError):
            ExternalDataType(name="Point")  # type: ignore[call-arg]

    def test_defaults_to_no_bazel_target(self) -> None:
        data_type = ExternalDataType(name="Point", header="geometry/point.hpp")

        self.assertIsNone(data_type.bazel_target)

    def test_accepts_bazel_labels(self) -> None:
        for label in ("//geometry:point", "@third_party//geometry:point", ":point", "//geometry"):
            with self.subTest(label=label):
                data_type = ExternalDataType(name="Point", header="geometry/point.hpp", bazel_target=label)

                self.assertEqual(data_type.bazel_target, label)

    def test_rejects_an_invalid_bazel_label(self) -> None:
        with self.assertRaisesRegex(ValidationError, "bazel_target must be a valid Bazel label"):
            ExternalDataType(name="Point", header="geometry/point.hpp", bazel_target="geometry:point")

    def test_rejects_a_blank_bazel_label(self) -> None:
        with self.assertRaisesRegex(ValidationError, "bazel_target must not be empty when provided"):
            ExternalDataType(name="Point", header="geometry/point.hpp", bazel_target="   ")


if __name__ == "__main__":
    unittest.main()
