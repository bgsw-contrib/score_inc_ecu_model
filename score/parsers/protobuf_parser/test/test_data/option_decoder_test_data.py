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

"""Build dynamic protobuf option fixtures for option-decoder tests."""

from __future__ import annotations

from google.protobuf import descriptor_pb2
from google.protobuf import descriptor_pool
from google.protobuf import message_factory


def field_option_extension_descriptor_set() -> descriptor_pb2.FileDescriptorSet:
    """Return custom field-option declarations used by option decoder tests."""
    descriptor_set = descriptor_pb2.FileDescriptorSet()
    extension_file = descriptor_set.file.add(
        name="field_options.proto",
        package="integration.option_test",
        syntax="proto2",
    )
    extension_file.dependency.append("google/protobuf/descriptor.proto")
    field_deployment = extension_file.message_type.add(name="FieldDeployment")
    field_deployment.field.add(
        name="transport",
        number=1,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
    )
    field_deployment.field.add(
        name="queue_depth",
        number=2,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_UINT32,
    )
    field_deployment.field.add(
        name="description",
        number=3,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
    )
    field_deployment.field.add(
        name="max_count",
        number=4,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_UINT32,
    )
    field_deployment.field.add(
        name="signed_limit",
        number=5,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_INT64,
    )
    extension_scope = extension_file.message_type.add(name="OptionExtensions")
    extension_scope.extension.add(
        name="field_note",
        number=50001,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
        extendee=".google.protobuf.FieldOptions",
    )
    extension_scope.extension.add(
        name="field_deployment",
        number=50002,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        type_name=".integration.option_test.FieldDeployment",
        extendee=".google.protobuf.FieldOptions",
    )
    extension_scope.extension.add(
        name="description",
        number=50003,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_UINT32,
        extendee=".google.protobuf.FieldOptions",
    )
    extension_file.extension.add(
        name="file_note",
        number=50004,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
        extendee=".google.protobuf.FieldOptions",
    )
    return descriptor_set


def field_options_with_custom_extensions(
    descriptor_set: descriptor_pb2.FileDescriptorSet,
    *,
    include_field_deployment: bool = False,
    include_numeric_description: bool = False,
    include_file_scoped_extension: bool = False,
) -> descriptor_pb2.FieldOptions:
    """Return field options populated through the fixture's custom extensions."""
    pool = descriptor_pool.DescriptorPool()
    descriptor_file = descriptor_pb2.FileDescriptorProto()
    descriptor_pb2.DESCRIPTOR.CopyToProto(descriptor_file)
    pool.Add(descriptor_file)
    for file_descriptor in descriptor_set.file:
        pool.Add(file_descriptor)

    dynamic_option_type = message_factory.GetMessageClass(pool.FindMessageTypeByName("google.protobuf.FieldOptions"))
    dynamic_options = dynamic_option_type()
    dynamic_options.Extensions[pool.FindExtensionByName("integration.option_test.OptionExtensions.field_note")] = (
        "custom value"
    )
    if include_field_deployment:
        field_deployment = dynamic_options.Extensions[
            pool.FindExtensionByName("integration.option_test.OptionExtensions.field_deployment")
        ]
        field_deployment.transport = "in_memory"
        field_deployment.queue_depth = 16
        field_deployment.description.append("Field description")
        field_deployment.max_count = 32
        field_deployment.signed_limit = -9007199254740991
    if include_numeric_description:
        dynamic_options.Extensions[pool.FindExtensionByName("integration.option_test.OptionExtensions.description")] = 7
    if include_file_scoped_extension:
        dynamic_options.Extensions[pool.FindExtensionByName("integration.option_test.file_note")] = (
            "file-scoped custom value"
        )

    options = descriptor_pb2.FieldOptions()
    options.ParseFromString(dynamic_options.SerializeToString())
    options.deprecated = True
    options.ctype = descriptor_pb2.FieldOptions.CORD
    return options
