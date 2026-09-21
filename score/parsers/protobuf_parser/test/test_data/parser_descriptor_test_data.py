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

"""Build protobuf descriptor test data for parser tests."""

from __future__ import annotations

from google.protobuf import descriptor_pb2

from score.parsers.protobuf_parser.option_decoder import (
    OptionValues,
)


_FIELD = descriptor_pb2.FieldDescriptorProto


class DescriptorFixtureBuilder:
    """Construct one protobuf file descriptor and its containing descriptor set."""

    def __init__(
        self,
        *,
        file_name: str,
        package: str,
        syntax: str = "proto3",
    ) -> None:
        self.descriptor_set = descriptor_pb2.FileDescriptorSet()
        self.file_descriptor = self.descriptor_set.file.add(
            name=file_name,
            package=package,
            syntax=syntax,
        )

    def add_message(
        self,
        name: str,
        *,
        parent: descriptor_pb2.DescriptorProto | None = None,
    ) -> descriptor_pb2.DescriptorProto:
        messages = parent.nested_type if parent is not None else self.file_descriptor.message_type
        return messages.add(name=name)

    def add_enum(
        self,
        name: str,
        *,
        parent: descriptor_pb2.DescriptorProto | None = None,
    ) -> descriptor_pb2.EnumDescriptorProto:
        enums = parent.enum_type if parent is not None else self.file_descriptor.enum_type
        return enums.add(name=name)

    @staticmethod
    def add_enum_value(
        enum_descriptor: descriptor_pb2.EnumDescriptorProto,
        *,
        name: str,
        number: int,
    ) -> None:
        enum_descriptor.value.add(name=name, number=number)

    @staticmethod
    def add_oneof(
        message_descriptor: descriptor_pb2.DescriptorProto,
        name: str,
    ) -> int:
        message_descriptor.oneof_decl.add(name=name)
        return len(message_descriptor.oneof_decl) - 1

    @staticmethod
    def add_map_entry(
        message_descriptor: descriptor_pb2.DescriptorProto,
        name: str,
    ) -> descriptor_pb2.DescriptorProto:
        entry = message_descriptor.nested_type.add(name=name)
        entry.options.map_entry = True
        return entry

    @staticmethod
    def add_field(
        message_descriptor: descriptor_pb2.DescriptorProto,
        *,
        name: str,
        number: int,
        field_type: int,
        label: int = _FIELD.LABEL_OPTIONAL,
        type_name: str = "",
        oneof_index: int | None = None,
        proto3_optional: bool = False,
    ) -> None:
        field_descriptor = message_descriptor.field.add()
        field_descriptor.name = name
        field_descriptor.number = number
        field_descriptor.label = label
        field_descriptor.type = field_type
        field_descriptor.type_name = type_name
        if oneof_index is not None:
            field_descriptor.oneof_index = oneof_index
        field_descriptor.proto3_optional = proto3_optional


def nested_references_descriptor_set() -> descriptor_pb2.FileDescriptorSet:
    fixture = DescriptorFixtureBuilder(
        file_name="nested_references.proto",
        package="integration.pipeline",
    )

    container = fixture.add_message("NestedTypeContainer")
    nested_payload = fixture.add_message("NestedPayload", parent=container)
    fixture.add_field(
        nested_payload,
        name="value",
        number=1,
        field_type=_FIELD.TYPE_STRING,
    )
    nested_state = fixture.add_enum("NestedState", parent=container)
    fixture.add_enum_value(nested_state, name="NESTED_STATE_UNSPECIFIED", number=0)
    fixture.add_enum_value(nested_state, name="NESTED_STATE_ACTIVE", number=1)

    top_level_state = fixture.add_enum("TopLevelState")
    fixture.add_enum_value(top_level_state, name="TOP_LEVEL_STATE_UNSPECIFIED", number=0)
    fixture.add_enum_value(top_level_state, name="TOP_LEVEL_STATE_ACTIVE", number=1)
    fixture.add_enum_value(top_level_state, name="TOP_LEVEL_STATE_ERROR", number=-1)

    consumer = fixture.add_message("NestedTypeConsumer")
    fixture.add_field(
        consumer,
        name="payload",
        number=1,
        field_type=_FIELD.TYPE_MESSAGE,
        type_name=".integration.pipeline.NestedTypeContainer.NestedPayload",
    )
    fixture.add_field(
        consumer,
        name="state",
        number=2,
        field_type=_FIELD.TYPE_ENUM,
        type_name=".integration.pipeline.NestedTypeContainer.NestedState",
    )
    fixture.add_field(
        consumer,
        name="top_level_state",
        number=3,
        field_type=_FIELD.TYPE_ENUM,
        type_name=".integration.pipeline.TopLevelState",
    )

    return fixture.descriptor_set


def collections_descriptor_set() -> descriptor_pb2.FileDescriptorSet:
    fixture = DescriptorFixtureBuilder(
        file_name="collections_and_oneof.proto",
        package="integration.pipeline.collections",
    )

    state = fixture.add_enum("State")
    fixture.add_enum_value(state, name="STATE_UNSPECIFIED", number=0)
    fixture.add_enum_value(state, name="ACTIVE", number=1)

    child = fixture.add_message("Child")
    fixture.add_field(child, name="id", number=1, field_type=_FIELD.TYPE_UINT32)

    external = fixture.add_message("External")
    entry_state = fixture.add_enum("EntryState", parent=external)
    fixture.add_enum_value(entry_state, name="ENTRY_STATE_UNSPECIFIED", number=0)
    fixture.add_enum_value(entry_state, name="ENTRY_STATE_ACTIVE", number=1)
    counts_entry = fixture.add_message("CountsEntry", parent=external)
    fixture.add_field(counts_entry, name="id", number=1, field_type=_FIELD.TYPE_UINT32)

    shape = fixture.add_message("Shape")
    nickname_oneof_index = fixture.add_oneof(shape, "_nickname")
    identity_oneof_index = fixture.add_oneof(shape, "identity")
    map_entry = fixture.add_map_entry(shape, "CountsEntry")
    fixture.add_field(map_entry, name="key", number=1, field_type=_FIELD.TYPE_STRING)
    fixture.add_field(
        map_entry,
        name="value",
        number=2,
        field_type=_FIELD.TYPE_MESSAGE,
        type_name=".integration.pipeline.collections.Child",
    )
    fixture.add_field(
        shape,
        name="nickname",
        number=1,
        field_type=_FIELD.TYPE_STRING,
        oneof_index=nickname_oneof_index,
        proto3_optional=True,
    )
    fixture.add_field(
        shape,
        name="counts",
        number=2,
        field_type=_FIELD.TYPE_MESSAGE,
        label=_FIELD.LABEL_REPEATED,
        type_name=".integration.pipeline.collections.Shape.CountsEntry",
    )
    fixture.add_field(
        shape,
        name="email",
        number=3,
        field_type=_FIELD.TYPE_STRING,
        oneof_index=identity_oneof_index,
    )
    fixture.add_field(
        shape,
        name="child",
        number=4,
        field_type=_FIELD.TYPE_MESSAGE,
        type_name=".integration.pipeline.collections.Child",
        oneof_index=identity_oneof_index,
    )
    fixture.add_field(
        shape,
        name="children",
        number=5,
        field_type=_FIELD.TYPE_MESSAGE,
        label=_FIELD.LABEL_REPEATED,
        type_name=".integration.pipeline.collections.Child",
    )
    fixture.add_field(
        shape,
        name="state",
        number=6,
        field_type=_FIELD.TYPE_ENUM,
        type_name=".integration.pipeline.collections.State",
    )
    fixture.add_field(
        shape,
        name="external_entry",
        number=7,
        field_type=_FIELD.TYPE_MESSAGE,
        type_name=".integration.pipeline.collections.External.CountsEntry",
    )

    return fixture.descriptor_set


def empty_descriptor_set(
    *,
    file_name: str,
    package: str,
    syntax: str = "proto3",
) -> descriptor_pb2.FileDescriptorSet:
    return DescriptorFixtureBuilder(
        file_name=file_name,
        package=package,
        syntax=syntax,
    ).descriptor_set


def runtime_and_application_descriptor_set() -> descriptor_pb2.FileDescriptorSet:
    descriptor_set = descriptor_pb2.FileDescriptorSet()
    runtime_descriptor = descriptor_pb2.FileDescriptorProto()
    descriptor_pb2.DESCRIPTOR.CopyToProto(runtime_descriptor)
    descriptor_set.file.add().CopyFrom(runtime_descriptor)
    descriptor_set.file.add(
        name="application.proto",
        package="test.parser",
        syntax="proto3",
    ).message_type.add(name="Application")
    return descriptor_set


def primitive_values_descriptor_set() -> descriptor_pb2.FileDescriptorSet:
    fixture = DescriptorFixtureBuilder(
        file_name="primitive_values.proto",
        package="test.parser",
    )
    message = fixture.add_message("PrimitiveValues")
    for field_number, (field_name, field_type) in enumerate(
        (
            ("double_value", _FIELD.TYPE_DOUBLE),
            ("float_value", _FIELD.TYPE_FLOAT),
            ("int64_value", _FIELD.TYPE_INT64),
            ("uint64_value", _FIELD.TYPE_UINT64),
            ("int32_value", _FIELD.TYPE_INT32),
            ("fixed64_value", _FIELD.TYPE_FIXED64),
            ("fixed32_value", _FIELD.TYPE_FIXED32),
            ("bool_value", _FIELD.TYPE_BOOL),
            ("string_value", _FIELD.TYPE_STRING),
            ("bytes_value", _FIELD.TYPE_BYTES),
            ("uint32_value", _FIELD.TYPE_UINT32),
            ("sfixed32_value", _FIELD.TYPE_SFIXED32),
            ("sfixed64_value", _FIELD.TYPE_SFIXED64),
            ("sint32_value", _FIELD.TYPE_SINT32),
            ("sint64_value", _FIELD.TYPE_SINT64),
        ),
        start=1,
    ):
        fixture.add_field(
            message,
            name=field_name,
            number=field_number,
            field_type=field_type,
        )
    return fixture.descriptor_set


def metadata_descriptor_set() -> descriptor_pb2.FileDescriptorSet:
    fixture = DescriptorFixtureBuilder(
        file_name="metadata.proto",
        package="test.metadata",
    )
    state = fixture.add_enum("State")
    fixture.add_enum_value(state, name="STATE_UNSPECIFIED", number=0)
    envelope = fixture.add_message("Envelope")
    identity_oneof_index = fixture.add_oneof(envelope, "identity")
    fixture.add_field(
        envelope,
        name="email",
        number=1,
        field_type=_FIELD.TYPE_STRING,
        oneof_index=identity_oneof_index,
    )
    fixture.add_field(
        envelope,
        name="tags",
        number=2,
        field_type=_FIELD.TYPE_STRING,
        label=_FIELD.LABEL_REPEATED,
    )
    fixture.add_field(
        envelope,
        name="label",
        number=3,
        field_type=_FIELD.TYPE_STRING,
    )
    return fixture.descriptor_set


def metadata_option_values_by_message_type() -> dict[str, OptionValues]:
    return {
        "google.protobuf.FileOptions": OptionValues(
            description="File description",
            deployment_properties={"file": "value", "shared": "file"},
        ),
        "google.protobuf.MessageOptions": OptionValues(
            description="Message description",
            deployment_properties={"message": "value", "shared": "message"},
        ),
        "google.protobuf.EnumOptions": OptionValues(
            deployment_properties={"enum": "value"},
        ),
        "google.protobuf.OneofOptions": OptionValues(
            deployment_properties={"oneof": "value"},
        ),
        "google.protobuf.FieldOptions": OptionValues(
            description="Field description",
            deployment_properties={"field": "value"},
            repeated_max_count=32,
        ),
        "google.protobuf.EnumValueOptions": OptionValues(
            description="Enum value description",
            deployment_properties={"enum_value": "value"},
        ),
    }


def repeated_primitive_descriptor_set() -> descriptor_pb2.FileDescriptorSet:
    fixture = DescriptorFixtureBuilder(
        file_name="repeated_primitive.proto",
        package="test.parser",
    )
    container = fixture.add_message("Container")
    fixture.add_field(
        container,
        name="labels",
        number=1,
        field_type=_FIELD.TYPE_STRING,
        label=_FIELD.LABEL_REPEATED,
    )
    return fixture.descriptor_set


def user_defined_map_descriptor_set() -> descriptor_pb2.FileDescriptorSet:
    fixture = DescriptorFixtureBuilder(
        file_name="user_defined_map.proto",
        package="test.parser",
    )
    fixture.add_message("Key")
    fixture.add_message("Value")
    container = fixture.add_message("Container")
    map_entry = fixture.add_map_entry(container, "EntriesEntry")
    fixture.add_field(
        map_entry,
        name="key",
        number=1,
        field_type=_FIELD.TYPE_MESSAGE,
        type_name=".test.parser.Key",
    )
    fixture.add_field(
        map_entry,
        name="value",
        number=2,
        field_type=_FIELD.TYPE_MESSAGE,
        type_name=".test.parser.Value",
    )
    fixture.add_field(
        container,
        name="entries",
        number=1,
        field_type=_FIELD.TYPE_MESSAGE,
        label=_FIELD.LABEL_REPEATED,
        type_name=".test.parser.Container.EntriesEntry",
    )
    return fixture.descriptor_set


def enum_size_descriptor_set() -> descriptor_pb2.FileDescriptorSet:
    fixture = DescriptorFixtureBuilder(
        file_name="enum_size.proto",
        package="test.parser",
    )
    state = fixture.add_enum("State")
    fixture.add_enum_value(state, name="STATE_UNSPECIFIED", number=0)
    return fixture.descriptor_set


def malformed_descriptor_cases() -> tuple[tuple[str, descriptor_pb2.FileDescriptorSet, str], ...]:
    missing_message_name = DescriptorFixtureBuilder(
        file_name="missing_message_name.proto",
        package="test.parser",
    )
    missing_message_name.add_message("")

    missing_field_name = DescriptorFixtureBuilder(
        file_name="missing_field_name.proto",
        package="test.parser",
    )
    missing_field_name_message = missing_field_name.add_message("Container")
    missing_field_name.add_field(
        missing_field_name_message,
        name="",
        number=1,
        field_type=_FIELD.TYPE_STRING,
    )

    unsupported_field_type = DescriptorFixtureBuilder(
        file_name="unsupported_field_type.proto",
        package="test.parser",
    )
    unsupported_field_type_message = unsupported_field_type.add_message("Container")
    unsupported_field_type.add_field(
        unsupported_field_type_message,
        name="unknown",
        number=1,
        field_type=_FIELD.TYPE_MESSAGE,
    )

    malformed_type_name = DescriptorFixtureBuilder(
        file_name="malformed_type_name.proto",
        package="test.parser",
    )
    malformed_type_name_message = malformed_type_name.add_message("Container")
    malformed_type_name.add_field(
        malformed_type_name_message,
        name="unknown",
        number=1,
        field_type=_FIELD.TYPE_MESSAGE,
        type_name=".",
    )

    top_level_map_entry = DescriptorFixtureBuilder(
        file_name="top_level_map_entry.proto",
        package="test.parser",
    )
    top_level_map_entry.add_message("Entry").options.map_entry = True

    invalid_oneof_index = DescriptorFixtureBuilder(
        file_name="invalid_oneof_index.proto",
        package="test.parser",
    )
    invalid_oneof_index_message = invalid_oneof_index.add_message("Container")
    invalid_oneof_index.add_field(
        invalid_oneof_index_message,
        name="choice",
        number=1,
        field_type=_FIELD.TYPE_STRING,
        oneof_index=0,
    )

    malformed_map_entry = DescriptorFixtureBuilder(
        file_name="malformed_map_entry.proto",
        package="test.parser",
    )
    malformed_map_entry_message = malformed_map_entry.add_message("Container")
    map_entry = malformed_map_entry.add_map_entry(
        malformed_map_entry_message,
        "EntriesEntry",
    )
    malformed_map_entry.add_field(
        map_entry,
        name="value",
        number=2,
        field_type=_FIELD.TYPE_STRING,
    )
    malformed_map_entry.add_field(
        malformed_map_entry_message,
        name="entries",
        number=1,
        field_type=_FIELD.TYPE_MESSAGE,
        label=_FIELD.LABEL_REPEATED,
        type_name=".test.parser.Container.EntriesEntry",
    )

    return (
        (
            "missing_message_name",
            missing_message_name.descriptor_set,
            "message descriptor has no name",
        ),
        (
            "missing_field_name",
            missing_field_name.descriptor_set,
            "field descriptor has no name",
        ),
        (
            "unsupported_field_type",
            unsupported_field_type.descriptor_set,
            "unsupported field type 'TYPE_MESSAGE'",
        ),
        (
            "malformed_type_name",
            malformed_type_name.descriptor_set,
            "field type has no protobuf type name",
        ),
        (
            "top_level_map_entry",
            top_level_map_entry.descriptor_set,
            "top-level map entry is unsupported",
        ),
        (
            "invalid_oneof_index",
            invalid_oneof_index.descriptor_set,
            "malformed oneof descriptor",
        ),
        (
            "malformed_map_entry",
            malformed_map_entry.descriptor_set,
            "malformed descriptor map entry",
        ),
    )


def conflicting_descriptor_cases() -> tuple[tuple[descriptor_pb2.FileDescriptorSet, str], ...]:
    ambiguous_map_entries = DescriptorFixtureBuilder(
        file_name="ambiguous_map_entries.proto",
        package="test.parser",
    )
    ambiguous_container = ambiguous_map_entries.add_message("Container")
    for _ in range(2):
        entry = ambiguous_map_entries.add_map_entry(ambiguous_container, "EntriesEntry")
        ambiguous_map_entries.add_field(
            entry,
            name="key",
            number=1,
            field_type=_FIELD.TYPE_STRING,
        )
        ambiguous_map_entries.add_field(
            entry,
            name="value",
            number=2,
            field_type=_FIELD.TYPE_STRING,
        )
    ambiguous_map_entries.add_field(
        ambiguous_container,
        name="entries",
        number=1,
        field_type=_FIELD.TYPE_MESSAGE,
        label=_FIELD.LABEL_REPEATED,
        type_name=".test.parser.Container.EntriesEntry",
    )

    duplicate_definitions = DescriptorFixtureBuilder(
        file_name="duplicate_definitions.proto",
        package="test.parser",
    )
    duplicate_definitions.add_message("Duplicate")
    duplicate_definitions.add_message("Duplicate")

    return (
        (
            ambiguous_map_entries.descriptor_set,
            "Malformed descriptor map entry",
        ),
        (
            duplicate_definitions.descriptor_set,
            "Conflicting generated model definition for key",
        ),
    )
