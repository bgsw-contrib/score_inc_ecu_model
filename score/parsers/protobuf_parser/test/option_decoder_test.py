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

"""Skeleton for protobuf option decoder unit tests."""

from __future__ import annotations

import unittest

from google.protobuf import descriptor_pb2

from score.parsers.protobuf_parser.common import (
    ProtoTransformerError,
)
from score.parsers.protobuf_parser.option_decoder import (
    OptionDecoder,
    OptionValues,
    repeated_dimension_max,
)
from score.parsers.protobuf_parser.test.test_data.option_decoder_test_data import (
    field_option_extension_descriptor_set,
    field_options_with_custom_extensions,
)


class ProtobufOptionDecoderUnitTest(unittest.TestCase):
    """Test protobuf option decoding without source compilation."""

    def test_opt_01_given_empty_options_when_decoded_then_returns_default_values(self) -> None:
        option_values = OptionDecoder(descriptor_pb2.FileDescriptorSet()).decode(descriptor_pb2.FieldOptions())

        self.assertEqual(option_values, OptionValues())

    def test_opt_02_given_explicit_standard_options_when_decoded_then_keeps_full_names(
        self,
    ) -> None:
        options = descriptor_pb2.FieldOptions(
            deprecated=True,
            ctype=descriptor_pb2.FieldOptions.CORD,
        )

        option_values = OptionDecoder(descriptor_pb2.FileDescriptorSet()).decode(options)

        self.assertEqual(
            option_values,
            OptionValues(
                deployment_properties={
                    "google.protobuf.FieldOptions.deprecated": True,
                    "google.protobuf.FieldOptions.ctype": "CORD",
                }
            ),
        )

    def test_opt_03_given_scalar_custom_option_when_decoded_then_keeps_value(self) -> None:
        descriptor_set = field_option_extension_descriptor_set()
        options = field_options_with_custom_extensions(descriptor_set)

        option_values = OptionDecoder(descriptor_set).decode(options)

        self.assertEqual(
            option_values.deployment_properties["integration.option_test.OptionExtensions.field_note"],
            "custom value",
        )

    def test_opt_04_given_message_custom_option_when_decoded_then_flattens_properties(
        self,
    ) -> None:
        descriptor_set = field_option_extension_descriptor_set()
        options = field_options_with_custom_extensions(
            descriptor_set,
            include_field_deployment=True,
        )

        option_values = OptionDecoder(descriptor_set).decode(options)

        self.assertEqual(option_values.description, "Field description")
        self.assertEqual(
            {key: value for key, value in option_values.deployment_properties.items() if ".field_deployment." in key},
            {
                "integration.option_test.OptionExtensions.field_deployment.transport": "in_memory",
                "integration.option_test.OptionExtensions.field_deployment.queue_depth": 16,
                "integration.option_test.OptionExtensions.field_deployment.signed_limit": "-9007199254740991",
            },
        )
        self.assertNotIn(
            "integration.option_test.OptionExtensions.field_deployment.description",
            option_values.deployment_properties,
        )

    def test_opt_05_given_repeated_max_count_when_decoded_then_keeps_it_separately(
        self,
    ) -> None:
        descriptor_set = field_option_extension_descriptor_set()
        options = field_options_with_custom_extensions(
            descriptor_set,
            include_field_deployment=True,
        )

        option_values = OptionDecoder(descriptor_set).decode(options)

        self.assertEqual(option_values.repeated_max_count, 32)
        self.assertNotIn(
            "integration.option_test.OptionExtensions.field_deployment.max_count",
            option_values.deployment_properties,
        )

    def test_opt_06_given_integer_max_count_when_normalized_then_returns_same_integer(self) -> None:
        self.assertEqual(repeated_dimension_max(32), 32)

    def test_opt_07_given_standard_and_custom_options_when_decoded_then_keeps_both_values(
        self,
    ) -> None:
        descriptor_set = field_option_extension_descriptor_set()
        options = field_options_with_custom_extensions(descriptor_set)

        option_values = OptionDecoder(descriptor_set).decode(options)

        self.assertEqual(
            option_values,
            OptionValues(
                deployment_properties={
                    "google.protobuf.FieldOptions.deprecated": True,
                    "google.protobuf.FieldOptions.ctype": "CORD",
                    "integration.option_test.OptionExtensions.field_note": "custom value",
                }
            ),
        )

    def test_opt_08_given_missing_option_descriptor_dependency_when_constructed_then_raises_error(
        self,
    ) -> None:
        descriptor_set = descriptor_pb2.FileDescriptorSet()
        file_descriptor = descriptor_set.file.add(name="consumer.proto", syntax="proto3")
        file_descriptor.dependency.append("missing.proto")

        with self.assertRaises(ProtoTransformerError) as error:
            OptionDecoder(descriptor_set)

        self.assertEqual(
            str(error.exception),
            "Cannot build protobuf option descriptor pool; unresolved dependencies: consumer.proto: missing.proto",
        )

    def test_opt_09_given_unsupported_description_leaf_when_decoded_then_keeps_property(
        self,
    ) -> None:
        descriptor_set = field_option_extension_descriptor_set()
        options = field_options_with_custom_extensions(
            descriptor_set,
            include_numeric_description=True,
        )

        option_values = OptionDecoder(descriptor_set).decode(options)

        self.assertIsNone(option_values.description)
        self.assertEqual(
            option_values.deployment_properties["integration.option_test.OptionExtensions.description"],
            7,
        )

    def test_opt_10_given_file_and_message_scoped_extensions_when_decoded_then_keeps_fqns(
        self,
    ) -> None:
        descriptor_set = field_option_extension_descriptor_set()
        options = field_options_with_custom_extensions(
            descriptor_set,
            include_file_scoped_extension=True,
        )

        option_values = OptionDecoder(descriptor_set).decode(options)

        self.assertEqual(
            {
                name: value
                for name, value in option_values.deployment_properties.items()
                if name.startswith("integration.option_test")
            },
            {
                "integration.option_test.OptionExtensions.field_note": "custom value",
                "integration.option_test.file_note": "file-scoped custom value",
            },
        )

    def test_opt_11_given_standard_options_when_decoded_then_keeps_json_value_types(
        self,
    ) -> None:
        options = descriptor_pb2.FieldOptions(
            deprecated=True,
            ctype=descriptor_pb2.FieldOptions.CORD,
        )

        option_values = OptionDecoder(descriptor_pb2.FileDescriptorSet()).decode(options)
        deployment_properties = option_values.deployment_properties

        self.assertIs(
            deployment_properties["google.protobuf.FieldOptions.deprecated"],
            True,
        )
        self.assertIsInstance(
            deployment_properties["google.protobuf.FieldOptions.ctype"],
            str,
        )
        self.assertEqual(
            deployment_properties["google.protobuf.FieldOptions.ctype"],
            "CORD",
        )


if __name__ == "__main__":
    unittest.main()
