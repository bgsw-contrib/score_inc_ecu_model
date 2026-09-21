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

"""Test the public Protobuf descriptor-artifact API."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from google.protobuf import descriptor_pb2

from score.parsers.protobuf_parser.api import (
    ProtobufToDataTypeParser,
)
from score.parsers.protobuf_parser.common import (
    ProtoTransformerError,
)
from score.parsers.protobuf_parser.resolver import (
    ProtoResolverError,
)


_FIELD = descriptor_pb2.FieldDescriptorProto


def _proto3_file(name: str, package: str) -> descriptor_pb2.FileDescriptorProto:
    return descriptor_pb2.FileDescriptorProto(
        name=name,
        package=package,
        syntax="proto3",
    )


def _add_message(
    file_descriptor: descriptor_pb2.FileDescriptorProto,
    name: str,
) -> descriptor_pb2.DescriptorProto:
    return file_descriptor.message_type.add(name=name)


def _add_message_field(
    message_descriptor: descriptor_pb2.DescriptorProto,
    *,
    name: str,
    number: int,
    type_name: str,
) -> None:
    message_descriptor.field.add(
        name=name,
        number=number,
        label=_FIELD.LABEL_OPTIONAL,
        type=_FIELD.TYPE_MESSAGE,
        type_name=type_name,
    )


def _write_descriptor_artifact(
    directory: Path,
    artifact_name: str,
    *file_descriptors: descriptor_pb2.FileDescriptorProto,
) -> Path:
    descriptor_set = descriptor_pb2.FileDescriptorSet()
    for file_descriptor in file_descriptors:
        descriptor_set.file.add().CopyFrom(file_descriptor)
    artifact_path = directory / artifact_name
    artifact_path.write_bytes(descriptor_set.SerializeToString())
    return artifact_path


class ProtobufApiIntegrationTest(unittest.TestCase):
    """Exercise the public API without compiler or macro dependencies."""

    def test_api_01_parses_one_artifact_and_resolves_references(self) -> None:
        file_descriptor = _proto3_file("single.proto", "test.api")
        _add_message(file_descriptor, "Child")
        parent = _add_message(file_descriptor, "Parent")
        _add_message_field(
            parent,
            name="child",
            number=1,
            type_name=".test.api.Child",
        )

        with TemporaryDirectory() as temporary_directory:
            artifact_path = _write_descriptor_artifact(
                Path(temporary_directory),
                "single.pb",
                file_descriptor,
            )
            definitions_by_key = ProtobufToDataTypeParser.parse([artifact_path])

        child = definitions_by_key["test.api.Child"]
        parent_definition = definitions_by_key["test.api.Parent"]
        self.assertIs(parent_definition.fields[0].data_type, child)

    def test_api_02_combines_multiple_artifacts_before_resolving_references(self) -> None:
        child_file = _proto3_file("child.proto", "test.api")
        _add_message(child_file, "Child")
        parent_file = _proto3_file("parent.proto", "test.api")
        parent_file.dependency.append("child.proto")
        parent = _add_message(parent_file, "Parent")
        _add_message_field(
            parent,
            name="child",
            number=1,
            type_name=".test.api.Child",
        )

        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            child_artifact = _write_descriptor_artifact(
                directory,
                "child.pb",
                child_file,
            )
            parent_artifact = _write_descriptor_artifact(
                directory,
                "parent.pb",
                parent_file,
            )
            definitions_by_key = ProtobufToDataTypeParser.parse([child_artifact, parent_artifact])

        self.assertIs(
            definitions_by_key["test.api.Parent"].fields[0].data_type,
            definitions_by_key["test.api.Child"],
        )

    def test_api_03_returns_an_ordinary_mutable_dictionary(self) -> None:
        file_descriptor = _proto3_file("mutable.proto", "test.api")
        _add_message(file_descriptor, "Child")

        with TemporaryDirectory() as temporary_directory:
            artifact_path = _write_descriptor_artifact(
                Path(temporary_directory),
                "mutable.pb",
                file_descriptor,
            )
            definitions_by_key = ProtobufToDataTypeParser.parse([artifact_path])

        child = definitions_by_key["test.api.Child"]
        self.assertIsInstance(definitions_by_key, dict)
        definitions_by_key["test.api.Injected"] = child
        self.assertIs(definitions_by_key["test.api.Injected"], child)

    def test_api_04_propagates_descriptor_artifact_read_failures(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            missing_artifact = Path(temporary_directory) / "missing.pb"
            with self.assertRaisesRegex(RuntimeError, "Failed to read descriptor artifact"):
                ProtobufToDataTypeParser.parse([missing_artifact])

    def test_api_05_propagates_descriptor_transformer_failures(self) -> None:
        legacy_file = descriptor_pb2.FileDescriptorProto(
            name="legacy.proto",
            package="test.api",
            syntax="proto2",
        )

        with TemporaryDirectory() as temporary_directory:
            artifact_path = _write_descriptor_artifact(
                Path(temporary_directory),
                "legacy.pb",
                legacy_file,
            )
            with self.assertRaisesRegex(ProtoTransformerError, "only proto3 is supported"):
                ProtobufToDataTypeParser.parse([artifact_path])

    def test_api_06_promotes_unresolved_references_to_resolver_errors(self) -> None:
        file_descriptor = _proto3_file("unresolved.proto", "test.api")
        file_descriptor.dependency.append("google/protobuf/descriptor.proto")
        parent = _add_message(file_descriptor, "Parent")
        _add_message_field(
            parent,
            name="descriptor_set",
            number=1,
            type_name=".google.protobuf.FileDescriptorSet",
        )

        with TemporaryDirectory() as temporary_directory:
            artifact_path = _write_descriptor_artifact(
                Path(temporary_directory),
                "unresolved.pb",
                file_descriptor,
            )
            with self.assertRaisesRegex(
                ProtoResolverError,
                "unresolved_type: Cannot resolve type '.google.protobuf.FileDescriptorSet'",
            ):
                ProtobufToDataTypeParser.parse([artifact_path])


if __name__ == "__main__":
    unittest.main()
