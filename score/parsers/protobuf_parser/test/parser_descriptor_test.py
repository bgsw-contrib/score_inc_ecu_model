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

"""Test direct FileDescriptorSet-to-model conversion."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
import unittest
from unittest.mock import patch

from google.protobuf import descriptor_pb2

from score.parsers.protobuf_parser.common import (
    ProtoTransformerError,
    ReferenceTargetKind,
)
from score.parsers.protobuf_parser.transformer import (
    DescriptorSetTransformer,
    load_descriptor_sets,
)
from score.parsers.protobuf_parser.test.test_data.parser_descriptor_test_data import (
    collections_descriptor_set,
    conflicting_descriptor_cases,
    empty_descriptor_set,
    enum_size_descriptor_set,
    malformed_descriptor_cases,
    metadata_descriptor_set,
    metadata_option_values_by_message_type,
    nested_references_descriptor_set,
    primitive_values_descriptor_set,
    repeated_primitive_descriptor_set,
    runtime_and_application_descriptor_set,
    user_defined_map_descriptor_set,
)
from score.parsers.protobuf_parser.option_decoder import (
    OptionValues,
)
from score.ecu_model.data_types.array import ArrayDataType
from score.ecu_model.data_types.enum import EnumDataType
from score.ecu_model.data_types.map import MapDataType
from score.ecu_model.data_types.primitives import PrimitiveDataType
from score.ecu_model.data_types.struct import StructDataType
from score.ecu_model.data_types.union import UnionDataType


def _write_descriptor_artifact(
    directory: Path,
    artifact_name: str,
    descriptor_set: descriptor_pb2.FileDescriptorSet,
) -> Path:
    descriptor_path = directory / artifact_name
    descriptor_path.write_bytes(descriptor_set.SerializeToString())
    return descriptor_path


def _transform_descriptor_artifact(
    descriptor_set: descriptor_pb2.FileDescriptorSet,
    *,
    option_values_by_message_type: dict[str, OptionValues] | None = None,
    bypass_option_pool_validation: bool = False,
):
    with TemporaryDirectory() as temporary_directory:
        descriptor_path = _write_descriptor_artifact(
            Path(temporary_directory),
            "descriptor_set.pb",
            descriptor_set,
        )
        if bypass_option_pool_validation:
            with patch("score.parsers.protobuf_parser.transformer.OptionDecoder") as option_decoder:
                option_decoder.return_value.decode.return_value = OptionValues()
                transformer = DescriptorSetTransformer([descriptor_path])
        else:
            transformer = DescriptorSetTransformer([descriptor_path])
        if option_values_by_message_type is None:
            return transformer.transform()
        with patch.object(
            transformer,
            "_decoded_option_values",
            side_effect=lambda options: option_values_by_message_type.get(
                options.DESCRIPTOR.full_name,
                OptionValues(),
            ),
        ):
            return transformer.transform()


class ProtobufTransformerDescriptorUnitTest(unittest.TestCase):
    """Test descriptor transformation without a compiler or resolver."""

    def _assert_metadata(
        self,
        subject: Any,
        *,
        description: str | None,
        deployment_properties: dict[str, str],
    ) -> None:
        self.assertEqual(subject.description, description)
        self.assertEqual(subject.deployment_properties, deployment_properties)

    def _assert_inline_array(
        self,
        data_type: Any,
        *,
        dimension_min: int = 0,
    ) -> ArrayDataType:
        self.assertIsInstance(data_type, ArrayDataType)
        self.assertTrue(data_type.is_inline)
        self.assertIsNone(data_type.name)
        self.assertEqual(data_type.dimension_min, dimension_min)
        return data_type

    def test_par_01_loads_combines_and_reports_descriptor_artifacts(self) -> None:
        first_descriptor_set = empty_descriptor_set(
            file_name="first.proto",
            package="test.parser",
        )
        second_descriptor_set = empty_descriptor_set(
            file_name="second.proto",
            package="test.parser",
        )

        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            first_artifact = _write_descriptor_artifact(
                directory,
                "first.pb",
                first_descriptor_set,
            )
            second_artifact = _write_descriptor_artifact(
                directory,
                "second.pb",
                second_descriptor_set,
            )
            combined = load_descriptor_sets([first_artifact, second_artifact])

        self.assertEqual(
            [file_descriptor.name for file_descriptor in combined.file],
            ["first.proto", "second.proto"],
        )

        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            missing_artifact = directory / "missing.pb"
            with self.assertRaisesRegex(RuntimeError, "Failed to read descriptor artifact"):
                load_descriptor_sets([missing_artifact])

            corrupt_artifact = directory / "corrupt.pb"
            corrupt_artifact.write_bytes(b"\x80")
            with self.assertRaisesRegex(RuntimeError, "Failed to read descriptor artifact"):
                load_descriptor_sets([corrupt_artifact])

    def test_par_02_handles_empty_and_runtime_descriptor_files(self) -> None:
        transformed_result = _transform_descriptor_artifact(runtime_and_application_descriptor_set())

        self.assertEqual(list(transformed_result.definitions_by_key), ["test.parser.Application"])

        empty_transformed_result = _transform_descriptor_artifact(
            empty_descriptor_set(
                file_name="empty.proto",
                package="test.parser",
            )
        )
        self.assertEqual(empty_transformed_result.definitions_by_key, {})
        self.assertEqual(empty_transformed_result.unresolved_references, [])

    def test_par_03_rejects_unsupported_syntax_and_malformed_packages(self) -> None:
        for name, syntax, package, message in (
            ("unspecified.proto", "", "test.parser", "only proto3 is supported"),
            ("legacy.proto", "proto2", "test.parser", "only proto3 is supported"),
            ("bad_package.proto", "proto3", "test..parser", "malformed protobuf package"),
        ):
            with self.subTest(name=name):
                descriptor_set = empty_descriptor_set(
                    file_name=name,
                    package=package,
                    syntax=syntax,
                )

                with self.assertRaisesRegex(ProtoTransformerError, message):
                    _transform_descriptor_artifact(descriptor_set)

    def test_par_04_registers_definitions_and_builtin_primitives(self) -> None:
        expected_fields = {
            "double_value": PrimitiveDataType.DOUBLE,
            "float_value": PrimitiveDataType.FLOAT,
            "int64_value": PrimitiveDataType.INT64,
            "uint64_value": PrimitiveDataType.UINT64,
            "int32_value": PrimitiveDataType.INT32,
            "fixed64_value": PrimitiveDataType.UINT64,
            "fixed32_value": PrimitiveDataType.UINT32,
            "bool_value": PrimitiveDataType.BOOL,
            "string_value": PrimitiveDataType.STRING,
            "bytes_value": PrimitiveDataType.BYTES,
            "uint32_value": PrimitiveDataType.UINT32,
            "sfixed32_value": PrimitiveDataType.INT32,
            "sfixed64_value": PrimitiveDataType.INT64,
            "sint32_value": PrimitiveDataType.INT32,
            "sint64_value": PrimitiveDataType.INT64,
        }
        transformed_result = _transform_descriptor_artifact(primitive_values_descriptor_set())

        fields = {
            field.name.as_str: field.data_type
            for field in transformed_result.definitions_by_key["test.parser.PrimitiveValues"].fields
        }
        for field_name, expected_type in expected_fields.items():
            with self.subTest(field_name=field_name):
                self.assertIs(fields[field_name], expected_type)
        self.assertIs(fields["fixed32_value"], fields["uint32_value"])
        self.assertIs(fields["sfixed32_value"], fields["sint32_value"])
        self.assertIs(fields["fixed64_value"], fields["uint64_value"])
        self.assertIs(fields["sfixed64_value"], fields["sint64_value"])

        nested_transformed_result = _transform_descriptor_artifact(nested_references_descriptor_set())
        nested_definitions = nested_transformed_result.definitions_by_key
        nested_struct = nested_definitions["integration.pipeline.NestedTypeContainer.NestedPayload"]
        nested_enum = nested_definitions["integration.pipeline.NestedTypeContainer.NestedState"]
        top_level_enum = nested_definitions["integration.pipeline.TopLevelState"]

        self.assertIsInstance(nested_struct, StructDataType)
        self.assertIsInstance(nested_enum, EnumDataType)
        self.assertIsInstance(top_level_enum, EnumDataType)
        self.assertEqual(nested_struct.source_uri, "nested_references.proto")
        self.assertEqual(top_level_enum.source_uri, "nested_references.proto")
        self.assertEqual(
            [(value.name.as_str, value.value) for value in top_level_enum.values],
            [
                ("TOP_LEVEL_STATE_UNSPECIFIED", 0),
                ("TOP_LEVEL_STATE_ACTIVE", 1),
                ("TOP_LEVEL_STATE_ERROR", -1),
            ],
        )
        self.assertEqual(top_level_enum.size, 32)
        self.assertTrue(top_level_enum.signed)
        nested_container = nested_definitions["integration.pipeline.NestedTypeContainer"]
        self.assertIs(nested_container.nested_structs[0], nested_struct)
        self.assertIs(nested_container.nested_enums[0], nested_enum)

    def test_par_05_converts_direct_primitive_and_user_defined_fields(self) -> None:
        primitive_transformed_result = _transform_descriptor_artifact(primitive_values_descriptor_set())
        primitive_field = primitive_transformed_result.definitions_by_key["test.parser.PrimitiveValues"].fields[0]
        self.assertEqual(primitive_field.name.as_str, "double_value")
        self.assertEqual(primitive_field.field_number, 1)
        self.assertIs(primitive_field.data_type, PrimitiveDataType.DOUBLE)

        nested_transformed_result = _transform_descriptor_artifact(nested_references_descriptor_set())
        consumer = nested_transformed_result.definitions_by_key["integration.pipeline.NestedTypeConsumer"]
        fields = {field.name.as_str: field for field in consumer.fields}
        self.assertEqual(fields["payload"].field_number, 1)
        self.assertEqual(
            fields["payload"].data_type.as_str,
            "integration.pipeline.NestedTypeContainer.NestedPayload",
        )
        self.assertEqual(
            fields["state"].data_type.as_str,
            "integration.pipeline.NestedTypeContainer.NestedState",
        )
        self.assertEqual(
            fields["top_level_state"].data_type.as_str,
            "integration.pipeline.TopLevelState",
        )
        self.assertEqual(
            [unresolved.protobuf_type_name for unresolved in nested_transformed_result.unresolved_references],
            [
                ".integration.pipeline.NestedTypeContainer.NestedPayload",
                ".integration.pipeline.NestedTypeContainer.NestedState",
                ".integration.pipeline.TopLevelState",
            ],
        )

    def test_par_06_converts_repeated_fields_to_inline_arrays(self) -> None:
        primitive_transformed_result = _transform_descriptor_artifact(repeated_primitive_descriptor_set())
        labels = primitive_transformed_result.definitions_by_key["test.parser.Container"].fields[0]
        labels_array = self._assert_inline_array(labels.data_type)
        self.assertIs(labels_array.data_type, PrimitiveDataType.STRING)
        self.assertEqual(primitive_transformed_result.unresolved_references, [])

        collection_transformed_result = _transform_descriptor_artifact(collections_descriptor_set())
        shape = collection_transformed_result.definitions_by_key["integration.pipeline.collections.Shape"]
        fields = {field.name.as_str: field for field in shape.fields}
        children_array = self._assert_inline_array(fields["children"].data_type)
        self.assertEqual(
            children_array.data_type.as_str,
            "integration.pipeline.collections.Child",
        )
        self.assertEqual(
            [reference.target.kind for reference in collection_transformed_result.unresolved_references],
            [
                ReferenceTargetKind.MAP_VALUE_TYPE,
                ReferenceTargetKind.FIELD_DATA_TYPE,
                ReferenceTargetKind.ARRAY_ELEMENT_TYPE,
                ReferenceTargetKind.FIELD_DATA_TYPE,
                ReferenceTargetKind.FIELD_DATA_TYPE,
            ],
        )

    def test_par_07_converts_map_entries_and_collects_map_references(self) -> None:
        transformed_result = _transform_descriptor_artifact(
            user_defined_map_descriptor_set(),
            bypass_option_pool_validation=True,
        )

        entries = transformed_result.definitions_by_key["test.parser.Container"].fields[0]
        self.assertIsInstance(entries.data_type, MapDataType)
        self.assertIsNone(entries.data_type.name)
        self.assertTrue(entries.data_type.is_inline)
        self.assertEqual(entries.data_type.key_type.as_str, "test.parser.Key")
        self.assertEqual(entries.data_type.value_type.as_str, "test.parser.Value")
        self.assertEqual(
            [reference.target.kind for reference in transformed_result.unresolved_references],
            [ReferenceTargetKind.MAP_KEY_TYPE, ReferenceTargetKind.MAP_VALUE_TYPE],
        )

    def test_par_08_converts_real_oneofs_and_proto3_optional_fields(self) -> None:
        transformed_result = _transform_descriptor_artifact(collections_descriptor_set())
        shape = transformed_result.definitions_by_key["integration.pipeline.collections.Shape"]
        fields = {field.name.as_str: field for field in shape.fields}

        self.assertTrue(fields["nickname"].optional)
        self.assertEqual(fields["nickname"].field_number, 1)
        identity = fields["identity"].data_type
        self.assertIsInstance(identity, UnionDataType)
        self.assertEqual(identity.namespace.as_str, shape.fully_qualified_name)
        self.assertIs(fields["identity"].data_type, identity)
        self.assertIsNone(fields["identity"].field_number)
        self.assertEqual([field.name.as_str for field in identity.fields], ["email", "child"])
        self.assertEqual([field.field_number for field in identity.fields], [3, 4])

    def test_par_09_records_deferred_reference_owners_and_targets(self) -> None:
        map_transformed_result = _transform_descriptor_artifact(
            user_defined_map_descriptor_set(),
            bypass_option_pool_validation=True,
        )
        self.assertEqual(
            [
                (
                    reference.protobuf_type_name,
                    reference.target.kind,
                    reference.target.owner_definition_key,
                    reference.target.field.name.as_str,
                )
                for reference in map_transformed_result.unresolved_references
            ],
            [
                (
                    ".test.parser.Key",
                    ReferenceTargetKind.MAP_KEY_TYPE,
                    "test.parser.Container",
                    "entries",
                ),
                (
                    ".test.parser.Value",
                    ReferenceTargetKind.MAP_VALUE_TYPE,
                    "test.parser.Container",
                    "entries",
                ),
            ],
        )

        collection_transformed_result = _transform_descriptor_artifact(collections_descriptor_set())
        self.assertEqual(
            [
                (
                    reference.target.kind,
                    reference.target.owner_definition_key,
                    reference.target.field.name.as_str,
                    reference.target.field.field_number,
                )
                for reference in collection_transformed_result.unresolved_references
            ],
            [
                (
                    ReferenceTargetKind.MAP_VALUE_TYPE,
                    "integration.pipeline.collections.Shape",
                    "counts",
                    2,
                ),
                (
                    ReferenceTargetKind.FIELD_DATA_TYPE,
                    "integration.pipeline.collections.Shape.identity",
                    "child",
                    4,
                ),
                (
                    ReferenceTargetKind.ARRAY_ELEMENT_TYPE,
                    "integration.pipeline.collections.Shape",
                    "children",
                    5,
                ),
                (
                    ReferenceTargetKind.FIELD_DATA_TYPE,
                    "integration.pipeline.collections.Shape",
                    "state",
                    6,
                ),
                (
                    ReferenceTargetKind.FIELD_DATA_TYPE,
                    "integration.pipeline.collections.Shape",
                    "external_entry",
                    7,
                ),
            ],
        )

    def test_par_10_wires_controlled_options_to_model_locations(self) -> None:
        transformed_result = _transform_descriptor_artifact(
            metadata_descriptor_set(),
            option_values_by_message_type=metadata_option_values_by_message_type(),
        )

        state = transformed_result.definitions_by_key["test.metadata.State"]
        envelope = transformed_result.definitions_by_key["test.metadata.Envelope"]
        fields = {field.name.as_str: field for field in envelope.fields}
        identity = fields["identity"].data_type
        tags = fields["tags"].data_type

        self._assert_metadata(
            state,
            description="",
            deployment_properties={"file": "value", "shared": "file", "enum": "value"},
        )
        self._assert_metadata(
            state.values[0],
            description="Enum value description",
            deployment_properties={"enum_value": "value"},
        )
        self._assert_metadata(
            envelope,
            description="Message description",
            deployment_properties={"file": "value", "shared": "message", "message": "value"},
        )
        self.assertIsInstance(identity, UnionDataType)
        self._assert_metadata(
            identity,
            description="",
            deployment_properties={"file": "value", "shared": "file", "oneof": "value"},
        )
        self.assertIsInstance(tags, ArrayDataType)
        self.assertEqual(tags.dimension_max, 32)
        self._assert_metadata(
            fields["label"],
            description="Field description",
            deployment_properties={"field": "value"},
        )

    def test_par_11_inherits_file_deployment_options_and_applies_local_overrides(self) -> None:
        transformed_result = _transform_descriptor_artifact(
            metadata_descriptor_set(),
            option_values_by_message_type=metadata_option_values_by_message_type(),
        )

        state = transformed_result.definitions_by_key["test.metadata.State"]
        envelope = transformed_result.definitions_by_key["test.metadata.Envelope"]
        fields = {field.name.as_str: field for field in envelope.fields}
        identity = fields["identity"].data_type

        self.assertEqual(
            state.deployment_properties,
            {"file": "value", "shared": "file", "enum": "value"},
        )
        self.assertEqual(state.description, "")
        self.assertEqual(
            envelope.deployment_properties,
            {"file": "value", "shared": "message", "message": "value"},
        )
        self.assertEqual(envelope.description, "Message description")
        self.assertIsInstance(identity, UnionDataType)
        self.assertEqual(
            identity.deployment_properties,
            {"file": "value", "shared": "file", "oneof": "value"},
        )
        self.assertEqual(identity.description, "")
        self.assertEqual(fields["label"].deployment_properties, {"field": "value"})
        self.assertEqual(state.values[0].deployment_properties, {"enum_value": "value"})

    def test_par_12_applies_and_validates_enum_size_options(self) -> None:
        for option_value, expected_size in (
            ("ES_8", 8),
            ("ES_16", 16),
            ("ES_32", 32),
        ):
            with self.subTest(option_value=option_value):
                option_values = {
                    "google.protobuf.EnumOptions": OptionValues(
                        deployment_properties={"deployment.size": option_value},
                    )
                }
                transformed_result = _transform_descriptor_artifact(
                    enum_size_descriptor_set(),
                    option_values_by_message_type=option_values,
                )
                state = transformed_result.definitions_by_key["test.parser.State"]
                self.assertEqual(state.size, expected_size)
                self.assertFalse(state.signed)

                negative_value_descriptor_set = enum_size_descriptor_set()
                negative_value_descriptor_set.file[0].enum_type[0].value.add(
                    name="STATE_ERROR",
                    number=-1,
                )
                transformed_result = _transform_descriptor_artifact(
                    negative_value_descriptor_set,
                    option_values_by_message_type=option_values,
                )
                state = transformed_result.definitions_by_key["test.parser.State"]
                self.assertEqual(state.size, expected_size)
                self.assertTrue(state.signed)

        for option_value, expected_error in (
            ("ES_64", "unsupported enum size 'ES_64'"),
            (16, "enum deployment option size must be a string"),
        ):
            with self.subTest(option_value=option_value):
                with self.assertRaisesRegex(ProtoTransformerError, expected_error):
                    _transform_descriptor_artifact(
                        enum_size_descriptor_set(),
                        option_values_by_message_type={
                            "google.protobuf.EnumOptions": OptionValues(
                                deployment_properties={"deployment.size": option_value},
                            )
                        },
                    )

    def test_par_13_rejects_malformed_and_conflicting_descriptor_shapes(self) -> None:
        for case_name, descriptor_set, expected_error in malformed_descriptor_cases():
            with self.subTest(case_name=case_name):
                with self.assertRaisesRegex(ProtoTransformerError, expected_error):
                    _transform_descriptor_artifact(
                        descriptor_set,
                        bypass_option_pool_validation=True,
                    )

        for descriptor_set, expected_error in conflicting_descriptor_cases():
            with self.subTest(expected_error=expected_error):
                with self.assertRaisesRegex(ProtoTransformerError, expected_error):
                    _transform_descriptor_artifact(
                        descriptor_set,
                        bypass_option_pool_validation=True,
                    )


if __name__ == "__main__":
    unittest.main()
