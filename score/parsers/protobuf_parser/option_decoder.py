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

"""Decode standard and custom protobuf options into deployment metadata."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from google.protobuf import descriptor_pb2
from google.protobuf import descriptor_pool
from google.protobuf import json_format
from google.protobuf import message_factory
from google.protobuf.descriptor import Descriptor
from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.message import Message

from score.parsers.protobuf_parser.common import (
    ProtoTransformerError,
)


def _option_descriptor_pool(
    descriptor_set: descriptor_pb2.FileDescriptorSet,
) -> descriptor_pool.DescriptorPool:
    pool = descriptor_pool.DescriptorPool()
    descriptor_file = descriptor_pb2.FileDescriptorProto()
    descriptor_pb2.DESCRIPTOR.CopyToProto(descriptor_file)
    pool.Add(descriptor_file)

    available_files = {descriptor_file.name}
    remaining_files = [
        file_descriptor for file_descriptor in descriptor_set.file if file_descriptor.name != descriptor_file.name
    ]
    while remaining_files:
        deferred_files: list[descriptor_pb2.FileDescriptorProto] = []
        added_file = False
        for file_descriptor in remaining_files:
            if any(dependency not in available_files for dependency in file_descriptor.dependency):
                deferred_files.append(file_descriptor)
                continue
            pool.Add(file_descriptor)
            available_files.add(file_descriptor.name)
            added_file = True
        if not added_file:
            unresolved_dependencies = "; ".join(
                f"{file_descriptor.name}: {', '.join(sorted(set(file_descriptor.dependency) - available_files))}"
                for file_descriptor in deferred_files
            )
            raise ProtoTransformerError(
                f"Cannot build protobuf option descriptor pool; unresolved dependencies: {unresolved_dependencies}"
            )
        remaining_files = deferred_files

    return pool


def _extension_names_by_extendee(
    descriptor_set: descriptor_pb2.FileDescriptorSet,
    pool: descriptor_pool.DescriptorPool,
) -> dict[str, tuple[str, ...]]:
    names_by_extendee: dict[str, list[str]] = {}

    def collect_extension_names(extension_descriptors: Iterable[FieldDescriptor]) -> None:
        for extension_descriptor in extension_descriptors:
            extendee = extension_descriptor.containing_type
            if extendee is not None:
                names_by_extendee.setdefault(extendee.full_name, []).append(extension_descriptor.full_name)

    def collect_message_extensions(message_descriptor: Descriptor) -> None:
        collect_extension_names(message_descriptor.extensions_by_name.values())
        for nested_struct_descriptor in message_descriptor.nested_types:
            collect_message_extensions(nested_struct_descriptor)

    for file_descriptor_proto in descriptor_set.file:
        file_descriptor = pool.FindFileByName(file_descriptor_proto.name)
        collect_extension_names(file_descriptor.extensions_by_name.values())
        for message_descriptor in file_descriptor.message_types_by_name.values():
            collect_message_extensions(message_descriptor)

    return {extendee: tuple(extension_names) for extendee, extension_names in names_by_extendee.items()}


@dataclass(frozen=True)
class OptionValues:
    """Standard and custom option values mapped to deployment-model metadata."""

    description: str | None = None
    deployment_properties: dict[str, object] = field(default_factory=dict)
    repeated_max_count: object | None = None


def _description_lines(value: object) -> list[str] | None:
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        return None

    lines: list[str] = []
    for line in value:
        if not isinstance(line, str):
            return None
        lines.append(line)
    return lines


def _flatten_option_value(
    option_name: str,
    option_value: object,
) -> Iterable[tuple[str, object]]:
    if not isinstance(option_value, dict):
        yield option_name, option_value
        return

    for property_name, property_value in option_value.items():
        yield from _flatten_option_value(
            f"{option_name}.{property_name}",
            property_value,
        )


def _option_values(option_values: dict[str, object]) -> OptionValues:
    description_lines: list[str] = []
    description_is_set = False
    deployment_properties: dict[str, object] = {}
    repeated_max_count: object | None = None
    for option_name, option_value in option_values.items():
        for property_name, property_value in _flatten_option_value(
            option_name,
            option_value,
        ):
            property_leaf_name = property_name.rsplit(".", maxsplit=1)[-1]
            if property_leaf_name == "description":
                lines = _description_lines(property_value)
                if lines is not None:
                    description_lines.extend(lines)
                    description_is_set = True
                    continue
            elif property_leaf_name == "max_count":
                if repeated_max_count is None:
                    repeated_max_count = property_value
                continue
            deployment_properties[property_name] = property_value

    return OptionValues(
        description="\n".join(description_lines) if description_is_set else None,
        deployment_properties=deployment_properties,
        repeated_max_count=repeated_max_count,
    )


def _standard_option_values(options: Message) -> dict[str, object]:
    """Return explicitly set standard option fields keyed by their full names."""
    serialized_values = json_format.MessageToDict(
        options,
        preserving_proto_field_name=True,
    )
    return {
        option_field.full_name: serialized_values[option_field.name]
        for option_field, _ in options.ListFields()
        if not option_field.is_extension
    }


def repeated_dimension_max(max_count: object | None) -> int | None:
    """Return max_count supplied by a repeated field deployment option."""
    if max_count is None:
        return None
    if isinstance(max_count, int) and not isinstance(max_count, bool):
        return max_count
    if isinstance(max_count, str) and max_count.isascii() and max_count.isdecimal():
        return int(max_count)
    raise ProtoTransformerError("Repeated field deployment option max_count must be an integer")


class _CustomOptionReader:
    """Read custom protobuf options from a descriptor set without generated extensions."""

    def __init__(self, descriptor_set: descriptor_pb2.FileDescriptorSet):
        self._pool = _option_descriptor_pool(descriptor_set)
        self._extension_names_by_extendee = _extension_names_by_extendee(
            descriptor_set,
            self._pool,
        )
        self._dynamic_option_types: dict[str, type[Message]] = {}

    def option_values(
        self,
        options: Message,
    ) -> dict[str, object]:
        if not options.ByteSize():
            return {}

        option_type_name = options.DESCRIPTOR.full_name
        extension_names = self._extension_names_by_extendee.get(option_type_name)
        if extension_names is None:
            return {}

        dynamic_option_type = self._dynamic_option_types.get(option_type_name)
        if dynamic_option_type is None:
            option_descriptor = self._pool.FindMessageTypeByName(option_type_name)
            # Global extensions have no package-qualified name to look up.
            available_extension_names = {
                extension.full_name for extension in self._pool.FindAllExtensions(option_descriptor)
            }
            if not set(extension_names).issubset(available_extension_names):
                raise ProtoTransformerError(f"Cannot resolve custom protobuf options for '{option_type_name}'")
            dynamic_option_type = message_factory.GetMessageClass(option_descriptor)
            self._dynamic_option_types[option_type_name] = dynamic_option_type

        dynamic_options = dynamic_option_type()
        dynamic_options.ParseFromString(options.SerializeToString())
        serialized_values = json_format.MessageToDict(
            dynamic_options,
            preserving_proto_field_name=True,
        )
        return {
            option_field.full_name: serialized_values[f"[{option_field.full_name}]"]
            for option_field, _ in dynamic_options.ListFields()
            if option_field.is_extension
        }


class OptionDecoder:
    """Decode all explicitly set protobuf options in a descriptor set."""

    def __init__(self, descriptor_set: descriptor_pb2.FileDescriptorSet):
        self._custom_option_reader = _CustomOptionReader(descriptor_set)

    def decode(self, options: Message) -> OptionValues:
        if not options.ByteSize():
            return OptionValues()
        return _option_values(
            {
                **_standard_option_values(options),
                **self._custom_option_reader.option_values(options),
            }
        )
