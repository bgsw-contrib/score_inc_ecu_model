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

"""Convert official protobuf descriptors directly into deployment data models."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from google.protobuf import descriptor_pb2
from google.protobuf.message import DecodeError, Message

from score.parsers.protobuf_parser.common import (
    ProtoTransformerError,
    ReferenceTarget,
    ReferenceTargetKind,
    TransformResult,
    UnresolvedReference,
    package_parts,
    protobuf_fqn,
    protobuf_reference,
    qualified_name,
    require_name,
)
from score.parsers.protobuf_parser.option_decoder import (
    OptionDecoder,
    OptionValues,
    repeated_dimension_max,
)
from score.ecu_model.data_types.array import ArrayDataType
from score.ecu_model.data_types.common import DataTypeBase, DataTypeSource
from score.ecu_model.data_types.composite import DataTypeField
from score.ecu_model.data_types.enum import EnumDataType, EnumValue
from score.ecu_model.data_types.identifier import Identifier, QualifiedName
from score.ecu_model.data_types.map import MapDataType
from score.ecu_model.data_types.primitives import PrimitiveDataType
from score.ecu_model.data_types.struct import StructDataType
from score.ecu_model.data_types.union import UnionDataType

_PRIMITIVE_FIELD_TYPES: dict[int, PrimitiveDataType] = {
    descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE: PrimitiveDataType.DOUBLE,
    descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT: PrimitiveDataType.FLOAT,
    descriptor_pb2.FieldDescriptorProto.TYPE_INT64: PrimitiveDataType.INT64,
    descriptor_pb2.FieldDescriptorProto.TYPE_UINT64: PrimitiveDataType.UINT64,
    descriptor_pb2.FieldDescriptorProto.TYPE_INT32: PrimitiveDataType.INT32,
    descriptor_pb2.FieldDescriptorProto.TYPE_FIXED64: PrimitiveDataType.UINT64,
    descriptor_pb2.FieldDescriptorProto.TYPE_FIXED32: PrimitiveDataType.UINT32,
    descriptor_pb2.FieldDescriptorProto.TYPE_BOOL: PrimitiveDataType.BOOL,
    descriptor_pb2.FieldDescriptorProto.TYPE_STRING: PrimitiveDataType.STRING,
    descriptor_pb2.FieldDescriptorProto.TYPE_BYTES: PrimitiveDataType.BYTES,
    descriptor_pb2.FieldDescriptorProto.TYPE_UINT32: PrimitiveDataType.UINT32,
    descriptor_pb2.FieldDescriptorProto.TYPE_SFIXED32: PrimitiveDataType.INT32,
    descriptor_pb2.FieldDescriptorProto.TYPE_SFIXED64: PrimitiveDataType.INT64,
    descriptor_pb2.FieldDescriptorProto.TYPE_SINT32: PrimitiveDataType.INT32,
    descriptor_pb2.FieldDescriptorProto.TYPE_SINT64: PrimitiveDataType.INT64,
}

_ENUM_STORAGE_SIZES: dict[str, int] = {
    "ES_8": 8,
    "ES_16": 16,
    "ES_32": 32,
}

_DESCRIPTOR_PROTO_FILE_PATH = "google/protobuf/descriptor.proto"


def load_descriptor_sets(paths: Iterable[str | Path]) -> descriptor_pb2.FileDescriptorSet:
    """Read and combine FileDescriptorSet artifacts from paths."""
    descriptor_set = descriptor_pb2.FileDescriptorSet()
    for descriptor_set_path in paths:
        path = Path(descriptor_set_path)
        source = descriptor_pb2.FileDescriptorSet()
        try:
            source.ParseFromString(path.read_bytes())
        except (DecodeError, OSError) as error:
            raise RuntimeError(f"Failed to read descriptor artifact '{path}': {error}") from error
        descriptor_set.file.extend(source.file)
    return descriptor_set


class DescriptorSetTransformer:
    """Stateful implementation behind descriptor-set transformation."""

    def __init__(self, descriptor_set_paths: Iterable[str | Path]):
        self._descriptor_set = load_descriptor_sets(descriptor_set_paths)
        self._definitions_by_key: dict[str, DataTypeBase] = {}
        self._unresolved_references: list[UnresolvedReference] = []
        self._option_decoder = OptionDecoder(self._descriptor_set)

    def transform(self) -> TransformResult:
        for file_descriptor in self._descriptor_set.file:
            self._transform_file(file_descriptor)
        return TransformResult(
            definitions_by_key=self._definitions_by_key,
            unresolved_references=self._unresolved_references,
        )

    def _transform_file(self, file_descriptor: descriptor_pb2.FileDescriptorProto) -> None:
        file_path = file_descriptor.name
        if file_path == _DESCRIPTOR_PROTO_FILE_PATH:
            return
        syntax = file_descriptor.syntax or "proto2"
        if syntax != "proto3":
            raise ProtoTransformerError(f"{file_path}: only proto3 is supported, found '{syntax}'")

        namespace_parts = package_parts(file_descriptor.package, file_path)
        file_option_values = self._decoded_option_values(file_descriptor.options)

        for enum_descriptor in file_descriptor.enum_type:
            self._transform_enum(
                enum_descriptor,
                file_path=file_path,
                namespace_parts=namespace_parts,
                file_option_values=file_option_values,
            )
        for message_descriptor in file_descriptor.message_type:
            if message_descriptor.options.map_entry:
                raise ProtoTransformerError(f"{file_path}: top-level map entry is unsupported")
            self._transform_message(
                message_descriptor,
                file_path=file_path,
                namespace_parts=namespace_parts,
                file_option_values=file_option_values,
            )

    def _transform_enum(
        self,
        enum_descriptor: descriptor_pb2.EnumDescriptorProto,
        *,
        file_path: str,
        namespace_parts: tuple[str, ...],
        file_option_values: OptionValues,
    ) -> EnumDataType:
        enum_name = require_name(
            enum_descriptor.name,
            file_path=file_path,
            descriptor_kind="enum descriptor",
        )
        local_options = self._decoded_option_values(enum_descriptor.options)
        effective_options = self._merge_options(
            file_option_values,
            local_options,
        )
        enum_values = self._transform_enum_values(enum_descriptor)
        enum_size = self._enum_size(
            local_options.deployment_properties,
            file_path=file_path,
        )
        has_negative_values = any(enum_value.value is not None and enum_value.value < 0 for enum_value in enum_values)
        definition = EnumDataType(
            name=Identifier(enum_name),
            namespace=qualified_name(namespace_parts),
            source_kind=DataTypeSource.PROTOBUF,
            source_uri=file_path,
            description=effective_options.description or "",
            deployment_properties=effective_options.deployment_properties,
            allow_value_aliases=enum_descriptor.options.allow_alias,
            size=enum_size,
            signed=has_negative_values,
            values=enum_values,
        )
        self._append_definition(definition)
        return definition

    def _transform_message(
        self,
        message_descriptor: descriptor_pb2.DescriptorProto,
        *,
        file_path: str,
        namespace_parts: tuple[str, ...],
        file_option_values: OptionValues,
    ) -> StructDataType:
        message_name = require_name(
            message_descriptor.name,
            file_path=file_path,
            descriptor_kind="message descriptor",
        )
        local_options = self._decoded_option_values(message_descriptor.options)
        effective_options = self._merge_options(
            file_option_values,
            local_options,
        )
        definition = StructDataType(
            name=Identifier(message_name),
            namespace=qualified_name(namespace_parts),
            source_kind=DataTypeSource.PROTOBUF,
            source_uri=file_path,
            description=effective_options.description or "",
            deployment_properties=effective_options.deployment_properties,
            fields=(),
        )
        self._append_definition(definition)
        message_fqn_parts = (*namespace_parts, message_name)

        definition.nested_enums = tuple(
            self._transform_enum(
                enum_descriptor,
                file_path=file_path,
                namespace_parts=message_fqn_parts,
                file_option_values=file_option_values,
            )
            for enum_descriptor in message_descriptor.enum_type
        )
        definition.nested_structs = tuple(
            self._transform_message(
                nested_descriptor,
                file_path=file_path,
                namespace_parts=message_fqn_parts,
                file_option_values=file_option_values,
            )
            for nested_descriptor in message_descriptor.nested_type
            if not nested_descriptor.options.map_entry
        )

        field_oneof_indexes = tuple(
            self._real_oneof_index(message_descriptor, field_descriptor, file_path)
            for field_descriptor in message_descriptor.field
        )
        oneofs_by_index = self._create_oneofs(
            message_descriptor,
            parent=definition,
            file_path=file_path,
            file_option_values=file_option_values,
            real_oneof_indexes=frozenset(oneof_index for oneof_index in field_oneof_indexes if oneof_index is not None),
        )
        message_fields: list[DataTypeField] = []
        oneof_fields_by_index: dict[int, list[DataTypeField]] = {}
        for field_descriptor, oneof_index in zip(
            message_descriptor.field,
            field_oneof_indexes,
            strict=True,
        ):
            if oneof_index is not None:
                union = oneofs_by_index[oneof_index]
                if oneof_index not in oneof_fields_by_index:
                    message_fields.append(
                        DataTypeField(
                            name=Identifier(message_descriptor.oneof_decl[oneof_index].name),
                            data_type=union,
                        )
                    )
                    oneof_fields_by_index[oneof_index] = []
                oneof_fields_by_index[oneof_index].append(
                    self._transform_field(
                        field_descriptor,
                        message_descriptor=message_descriptor,
                        message_namespace=definition.namespace,
                        file_path=file_path,
                        namespace_parts=message_fqn_parts,
                        owner_definition=union,
                    )
                )
                continue

            message_fields.append(
                self._transform_field(
                    field_descriptor,
                    message_descriptor=message_descriptor,
                    message_namespace=definition.namespace,
                    file_path=file_path,
                    namespace_parts=message_fqn_parts,
                    owner_definition=definition,
                )
            )

        definition.fields = tuple(message_fields)
        for oneof_index, member_fields in oneof_fields_by_index.items():
            oneofs_by_index[oneof_index].fields = tuple(member_fields)

        return definition

    def _create_oneofs(
        self,
        message_descriptor: descriptor_pb2.DescriptorProto,
        *,
        parent: StructDataType,
        file_path: str,
        file_option_values: OptionValues,
        real_oneof_indexes: frozenset[int],
    ) -> dict[int, UnionDataType]:
        if parent.name is None:
            raise ProtoTransformerError(f"{file_path}: oneof parent has no name")
        parent_namespace = QualifiedName((*parent.namespace.names, parent.name))

        oneofs: dict[int, UnionDataType] = {}
        for index, oneof_descriptor in enumerate(message_descriptor.oneof_decl):
            if index not in real_oneof_indexes:
                continue
            oneof_name = require_name(
                oneof_descriptor.name,
                file_path=file_path,
                descriptor_kind="oneof descriptor",
            )
            local_options = self._decoded_option_values(oneof_descriptor.options)
            effective_options = self._merge_options(
                file_option_values,
                local_options,
            )
            union = UnionDataType(
                name=Identifier(oneof_name),
                namespace=parent_namespace,
                source_kind=DataTypeSource.PROTOBUF,
                source_uri=file_path,
                description=effective_options.description or "",
                deployment_properties=effective_options.deployment_properties,
                fields=(),
            )
            oneofs[index] = union
        return oneofs

    def _real_oneof_index(
        self,
        message_descriptor: descriptor_pb2.DescriptorProto,
        field_descriptor: descriptor_pb2.FieldDescriptorProto,
        file_path: str,
    ) -> int | None:
        if field_descriptor.proto3_optional or not field_descriptor.HasField("oneof_index"):
            return None
        oneof_index = field_descriptor.oneof_index
        if oneof_index < 0 or oneof_index >= len(message_descriptor.oneof_decl):
            raise ProtoTransformerError(f"{file_path}: malformed oneof descriptor for field '{field_descriptor.name}'")
        return oneof_index

    def _transform_field(
        self,
        field_descriptor: descriptor_pb2.FieldDescriptorProto,
        *,
        message_descriptor: descriptor_pb2.DescriptorProto,
        message_namespace: QualifiedName,
        file_path: str,
        namespace_parts: tuple[str, ...],
        owner_definition: StructDataType | UnionDataType,
    ) -> DataTypeField:
        field_name = require_name(
            field_descriptor.name,
            file_path=file_path,
            descriptor_kind="field descriptor",
        )
        map_entry = self._map_entry(
            message_descriptor,
            field_descriptor,
            namespace_parts=namespace_parts,
        )
        if map_entry is not None:
            return self._transform_map(
                field_descriptor,
                map_entry=map_entry,
                message_namespace=message_namespace,
                file_path=file_path,
                namespace_parts=namespace_parts,
                owner_definition=owner_definition,
            )

        data_type, raw_name = self._field_data_type(field_descriptor, file_path=file_path)
        field_option_values = self._decoded_option_values(field_descriptor.options)
        if field_descriptor.label == descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED:
            array_definition = ArrayDataType(
                name=None,
                namespace=message_namespace,
                source_kind=DataTypeSource.PROTOBUF,
                source_uri=file_path,
                data_type=data_type,
                is_inline=True,
                dimension_min=0,
                dimension_max=repeated_dimension_max(
                    field_option_values.repeated_max_count,
                ),
            )
            transformed_field = DataTypeField(
                name=Identifier(field_name),
                data_type=array_definition,
                field_number=field_descriptor.number,
                description=field_option_values.description or "",
                deployment_properties=field_option_values.deployment_properties,
            )
            if raw_name is not None:
                self._append_unresolved_reference(
                    raw_name,
                    file_path=file_path,
                    target=ReferenceTarget(
                        field=transformed_field,
                        owner_definition_key=owner_definition.fully_qualified_name,
                        kind=ReferenceTargetKind.ARRAY_ELEMENT_TYPE,
                    ),
                )
            return transformed_field

        transformed_field = DataTypeField(
            name=Identifier(field_name),
            data_type=data_type,
            field_number=field_descriptor.number,
            optional=field_descriptor.proto3_optional,
            description=field_option_values.description or "",
            deployment_properties=field_option_values.deployment_properties,
        )
        if raw_name is not None:
            self._append_unresolved_reference(
                raw_name,
                file_path=file_path,
                target=ReferenceTarget(
                    field=transformed_field,
                    owner_definition_key=owner_definition.fully_qualified_name,
                    kind=ReferenceTargetKind.FIELD_DATA_TYPE,
                ),
            )
        return transformed_field

    def _transform_map(
        self,
        field_descriptor: descriptor_pb2.FieldDescriptorProto,
        *,
        map_entry: descriptor_pb2.DescriptorProto,
        message_namespace: QualifiedName,
        file_path: str,
        namespace_parts: tuple[str, ...],
        owner_definition: StructDataType | UnionDataType,
    ) -> DataTypeField:
        fields_by_name = {entry_field.name: entry_field for entry_field in map_entry.field}
        try:
            key_descriptor = fields_by_name["key"]
            value_descriptor = fields_by_name["value"]
        except KeyError as error:
            raise ProtoTransformerError(f"{file_path}: malformed descriptor map entry '{map_entry.name}'") from error

        key_type, key_raw_name = self._field_data_type(key_descriptor, file_path=file_path)
        value_type, value_raw_name = self._field_data_type(value_descriptor, file_path=file_path)
        map_definition = MapDataType(
            name=None,
            namespace=message_namespace,
            source_kind=DataTypeSource.PROTOBUF,
            source_uri=file_path,
            key_type=key_type,
            value_type=value_type,
            is_inline=True,
        )
        field_option_values = self._decoded_option_values(field_descriptor.options)
        transformed_field = DataTypeField(
            name=Identifier(field_descriptor.name),
            data_type=map_definition,
            field_number=field_descriptor.number,
            description=field_option_values.description or "",
            deployment_properties=field_option_values.deployment_properties,
        )
        if key_raw_name is not None:
            self._append_unresolved_reference(
                key_raw_name,
                file_path=file_path,
                target=ReferenceTarget(
                    field=transformed_field,
                    owner_definition_key=owner_definition.fully_qualified_name,
                    kind=ReferenceTargetKind.MAP_KEY_TYPE,
                ),
            )
        if value_raw_name is not None:
            self._append_unresolved_reference(
                value_raw_name,
                file_path=file_path,
                target=ReferenceTarget(
                    field=transformed_field,
                    owner_definition_key=owner_definition.fully_qualified_name,
                    kind=ReferenceTargetKind.MAP_VALUE_TYPE,
                ),
            )
        return transformed_field

    def _transform_enum_values(
        self,
        enum_descriptor: descriptor_pb2.EnumDescriptorProto,
    ) -> tuple[EnumValue, ...]:
        values: list[EnumValue] = []
        for value in enum_descriptor.value:
            option_values = self._decoded_option_values(value.options)
            values.append(
                EnumValue(
                    name=Identifier(value.name),
                    value=value.number,
                    description=option_values.description or "",
                    deployment_properties=option_values.deployment_properties,
                )
            )
        return tuple(values)

    def _enum_size(
        self,
        deployment_properties: dict[str, object],
        *,
        file_path: str,
    ) -> int:
        enum_size = 32
        for option_name, option_value in deployment_properties.items():
            if option_name.rsplit(".", maxsplit=1)[-1] != "size":
                continue
            if not isinstance(option_value, str):
                raise ProtoTransformerError(f"{file_path}: enum deployment option size must be a string")
            parsed_enum_size = _ENUM_STORAGE_SIZES.get(option_value)
            if parsed_enum_size is None:
                raise ProtoTransformerError(f"{file_path}: unsupported enum size '{option_value}'")
            enum_size = parsed_enum_size
            break
        return enum_size

    def _decoded_option_values(
        self,
        options: Message,
    ) -> OptionValues:
        return self._option_decoder.decode(options)

    @staticmethod
    def _merge_options(
        inherited_options: OptionValues,
        local_options: OptionValues,
    ) -> OptionValues:
        return OptionValues(
            description=local_options.description,
            deployment_properties={
                **inherited_options.deployment_properties,
                **local_options.deployment_properties,
            },
            repeated_max_count=local_options.repeated_max_count,
        )

    def _field_data_type(
        self,
        field_descriptor: descriptor_pb2.FieldDescriptorProto,
        *,
        file_path: str,
    ) -> tuple[PrimitiveDataType | QualifiedName, str | None]:
        primitive_data_type = _PRIMITIVE_FIELD_TYPES.get(field_descriptor.type)
        if primitive_data_type is not None:
            return primitive_data_type, None
        if not field_descriptor.type_name:
            type_name = descriptor_pb2.FieldDescriptorProto.Type.Name(field_descriptor.type)
            raise ProtoTransformerError(f"{file_path}: unsupported field type '{type_name}'")
        raw_name = field_descriptor.type_name
        return protobuf_reference(raw_name, file_path=file_path), raw_name

    def _map_entry(
        self,
        message_descriptor: descriptor_pb2.DescriptorProto,
        field_descriptor: descriptor_pb2.FieldDescriptorProto,
        *,
        namespace_parts: tuple[str, ...],
    ) -> descriptor_pb2.DescriptorProto | None:
        if field_descriptor.type != descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE or not field_descriptor.type_name:
            return None
        field_type_name = field_descriptor.type_name.lstrip(".")
        matching_entries = [
            nested_descriptor
            for nested_descriptor in message_descriptor.nested_type
            if nested_descriptor.options.map_entry
            and field_type_name == protobuf_fqn((*namespace_parts, nested_descriptor.name))
        ]
        if len(matching_entries) > 1:
            raise ProtoTransformerError(
                f"Malformed descriptor map entry '{field_type_name}' for field '{field_descriptor.name}'"
            )
        return matching_entries[0] if matching_entries else None

    def _append_definition(self, definition: DataTypeBase) -> None:
        key = definition.fully_qualified_name
        if key in self._definitions_by_key:
            raise ProtoTransformerError(f"Conflicting generated model definition for key '{key}'")
        self._definitions_by_key[key] = definition

    def _append_unresolved_reference(
        self,
        raw_name: str,
        *,
        file_path: str,
        target: ReferenceTarget,
    ) -> None:
        self._unresolved_references.append(
            UnresolvedReference(
                protobuf_type_name=raw_name,
                file_path=file_path,
                target=target,
            )
        )
