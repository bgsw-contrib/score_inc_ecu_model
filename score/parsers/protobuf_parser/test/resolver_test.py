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

"""Test deferred Protobuf reference resolution."""

from __future__ import annotations

import unittest

from score.parsers.protobuf_parser.common import (
    ProtoResolverIssue,
    ReferenceTarget,
    ReferenceTargetKind,
    SourceSpan,
    UnresolvedReference,
)
from score.parsers.protobuf_parser.resolver import resolve_references
from score.ecu_model.data_types.array import ArrayDataType
from score.ecu_model.data_types.common import DataTypeSource
from score.ecu_model.data_types.composite import DataTypeField
from score.ecu_model.data_types.enum import EnumDataType
from score.ecu_model.data_types.identifier import Identifier, QualifiedName
from score.ecu_model.data_types.map import MapDataType
from score.ecu_model.data_types.struct import StructDataType
from score.ecu_model.data_types.union import UnionDataType


def _qualified_name(value: str) -> QualifiedName:
    return QualifiedName(tuple(Identifier(part) for part in value.split(".")))


def _struct(name: str, namespace: str) -> StructDataType:
    return StructDataType(
        name=Identifier(name),
        namespace=_qualified_name(namespace),
        source_kind=DataTypeSource.PROTOBUF,
        source_uri=f"{name.lower()}.proto",
    )


def _enum(name: str, namespace: str) -> EnumDataType:
    return EnumDataType(
        name=Identifier(name),
        namespace=_qualified_name(namespace),
        source_kind=DataTypeSource.PROTOBUF,
        source_uri=f"{name.lower()}.proto",
    )


def _unresolved_reference(
    *,
    protobuf_type_name: str,
    field: DataTypeField,
    owner_definition_key: str,
    kind: ReferenceTargetKind,
) -> UnresolvedReference:
    return UnresolvedReference(
        protobuf_type_name=protobuf_type_name,
        file_path="consumer.proto",
        target=ReferenceTarget(
            field=field,
            owner_definition_key=owner_definition_key,
            kind=kind,
        ),
    )


class ProtobufResolverUnitTest(unittest.TestCase):
    """Test name lookup and reference-target mutation in isolation."""

    def test_res_01_resolves_absolute_names_only_against_exact_protobuf_fqns(self) -> None:
        target = _struct("Target", "test.resolver")
        decoy = _struct("Target", "test.resolver.Owner")
        owner = _struct("Owner", "test.resolver")
        field = DataTypeField(
            name=Identifier("target"),
            data_type=_qualified_name(target.fully_qualified_name),
            field_number=1,
        )
        owner.fields = (field,)
        context = [
            _unresolved_reference(
                protobuf_type_name=".test.resolver.Target",
                field=field,
                owner_definition_key=owner.fully_qualified_name,
                kind=ReferenceTargetKind.FIELD_DATA_TYPE,
            )
        ]

        issues = resolve_references(
            context,
            {
                target.fully_qualified_name: target,
                decoy.fully_qualified_name: decoy,
                owner.fully_qualified_name: owner,
            },
        )

        self.assertEqual(issues, [])
        self.assertIs(field.data_type, target)

    def test_res_02_resolves_fully_qualified_nested_and_package_references(self) -> None:
        namespace = "integration.pipeline"
        nested_struct = _struct("NestedPayload", f"{namespace}.NestedTypeContainer")
        nested_enum = _enum("NestedState", f"{namespace}.NestedTypeContainer")
        top_level_enum = _enum("TopLevelState", namespace)
        consumer = _struct("NestedTypeConsumer", namespace)
        payload_field = DataTypeField(
            name=Identifier("payload"),
            data_type=_qualified_name(nested_struct.fully_qualified_name),
            field_number=1,
        )
        state_field = DataTypeField(
            name=Identifier("state"),
            data_type=_qualified_name(nested_enum.fully_qualified_name),
            field_number=2,
        )
        top_level_state_field = DataTypeField(
            name=Identifier("top_level_state"),
            data_type=_qualified_name(top_level_enum.fully_qualified_name),
            field_number=3,
        )
        consumer.fields = (payload_field, state_field, top_level_state_field)
        context = [
            _unresolved_reference(
                protobuf_type_name=".integration.pipeline.NestedTypeContainer.NestedPayload",
                field=payload_field,
                owner_definition_key=consumer.fully_qualified_name,
                kind=ReferenceTargetKind.FIELD_DATA_TYPE,
            ),
            _unresolved_reference(
                protobuf_type_name=".integration.pipeline.NestedTypeContainer.NestedState",
                field=state_field,
                owner_definition_key=consumer.fully_qualified_name,
                kind=ReferenceTargetKind.FIELD_DATA_TYPE,
            ),
            _unresolved_reference(
                protobuf_type_name=".integration.pipeline.TopLevelState",
                field=top_level_state_field,
                owner_definition_key=consumer.fully_qualified_name,
                kind=ReferenceTargetKind.FIELD_DATA_TYPE,
            ),
        ]

        issues = resolve_references(
            context,
            {
                definition.fully_qualified_name: definition
                for definition in (nested_struct, nested_enum, top_level_enum, consumer)
            },
        )

        self.assertEqual(issues, [])
        self.assertIs(payload_field.data_type, nested_struct)
        self.assertIs(state_field.data_type, nested_enum)
        self.assertIs(top_level_state_field.data_type, top_level_enum)

    def test_res_03_replaces_direct_field_references_with_definition_objects(self) -> None:
        target = _struct("Target", "test.resolver")
        owner = _struct("Owner", "test.resolver")
        field = DataTypeField(
            name=Identifier("target"),
            data_type=_qualified_name(target.fully_qualified_name),
            field_number=1,
        )
        owner.fields = (field,)
        context = [
            UnresolvedReference(
                protobuf_type_name=".test.resolver.Target",
                file_path="owner.proto",
                target=ReferenceTarget(
                    field=field,
                    owner_definition_key=owner.fully_qualified_name,
                    kind=ReferenceTargetKind.FIELD_DATA_TYPE,
                ),
            )
        ]
        definitions_by_key = {
            target.fully_qualified_name: target,
            owner.fully_qualified_name: owner,
        }

        issues = resolve_references(context, definitions_by_key)

        self.assertEqual(issues, [])
        self.assertIs(field.data_type, target)

    def test_res_04_replaces_only_array_element_references_with_definition_objects(self) -> None:
        namespace = "integration.pipeline.collections"
        child = _struct("Child", namespace)
        shape = _struct("Shape", namespace)
        array_field = DataTypeField(
            name=Identifier("children"),
            data_type=ArrayDataType(
                name=None,
                namespace=_qualified_name(namespace),
                source_kind=DataTypeSource.PROTOBUF,
                source_uri="shape.proto",
                data_type=_qualified_name(child.fully_qualified_name),
                is_inline=True,
                dimension_min=0,
            ),
            field_number=2,
        )
        shape.fields = (array_field,)
        context = [
            _unresolved_reference(
                protobuf_type_name=".integration.pipeline.collections.Child",
                field=array_field,
                owner_definition_key=shape.fully_qualified_name,
                kind=ReferenceTargetKind.ARRAY_ELEMENT_TYPE,
            ),
        ]
        definitions_by_key = {
            child.fully_qualified_name: child,
            shape.fully_qualified_name: shape,
        }

        issues = resolve_references(context, definitions_by_key)

        self.assertEqual(issues, [])
        self.assertIs(array_field.data_type.data_type, child)

    def test_res_05_replaces_map_key_and_value_references_independently(self) -> None:
        namespace = "integration.pipeline.collections"
        child = _struct("Child", namespace)
        shape = _struct("Shape", namespace)
        map_field = DataTypeField(
            name=Identifier("children_by_key"),
            data_type=MapDataType(
                namespace=_qualified_name(namespace),
                source_kind=DataTypeSource.PROTOBUF,
                source_uri="shape.proto",
                key_type=_qualified_name(child.fully_qualified_name),
                value_type=_qualified_name(child.fully_qualified_name),
                is_inline=True,
            ),
            field_number=3,
        )
        shape.fields = (map_field,)
        context = [
            _unresolved_reference(
                protobuf_type_name=".integration.pipeline.collections.Child",
                field=map_field,
                owner_definition_key=shape.fully_qualified_name,
                kind=ReferenceTargetKind.MAP_KEY_TYPE,
            ),
            _unresolved_reference(
                protobuf_type_name=".integration.pipeline.collections.Child",
                field=map_field,
                owner_definition_key=shape.fully_qualified_name,
                kind=ReferenceTargetKind.MAP_VALUE_TYPE,
            ),
        ]

        issues = resolve_references(
            context,
            {
                child.fully_qualified_name: child,
                shape.fully_qualified_name: shape,
            },
        )

        self.assertEqual(issues, [])
        self.assertIs(map_field.data_type.key_type, child)
        self.assertIs(map_field.data_type.value_type, child)

    def test_res_06_replaces_union_member_references_with_definition_objects(self) -> None:
        namespace = "integration.pipeline.collections"
        child = _struct("Child", namespace)
        shape = _struct("Shape", namespace)
        identity = UnionDataType(
            name=Identifier("identity"),
            namespace=_qualified_name(shape.fully_qualified_name),
            source_kind=DataTypeSource.PROTOBUF,
            source_uri="shape.proto",
        )
        union_member = DataTypeField(
            name=Identifier("child"),
            data_type=_qualified_name(child.fully_qualified_name),
            field_number=4,
        )
        identity.fields = (union_member,)
        shape.fields = (DataTypeField(name=Identifier("identity"), data_type=identity),)
        context = [
            _unresolved_reference(
                protobuf_type_name=".integration.pipeline.collections.Child",
                field=union_member,
                owner_definition_key=identity.fully_qualified_name,
                kind=ReferenceTargetKind.FIELD_DATA_TYPE,
            )
        ]

        issues = resolve_references(
            context,
            {
                child.fully_qualified_name: child,
                shape.fully_qualified_name: shape,
            },
        )

        self.assertEqual(issues, [])
        self.assertIs(union_member.data_type, child)

    def test_res_07_reports_an_unresolved_type_with_a_fallback_source_span(self) -> None:
        owner = _struct("Owner", "test.resolver")
        field = DataTypeField(
            name=Identifier("missing"),
            data_type=_qualified_name("test.resolver.Missing"),
            field_number=1,
        )
        owner.fields = (field,)
        unresolved = _unresolved_reference(
            protobuf_type_name=".test.resolver.Missing",
            field=field,
            owner_definition_key=owner.fully_qualified_name,
            kind=ReferenceTargetKind.FIELD_DATA_TYPE,
        )

        issues = resolve_references(
            [unresolved],
            {owner.fully_qualified_name: owner},
        )

        self.assertEqual(
            issues,
            [
                ProtoResolverIssue(
                    phase="resolver",
                    code="unresolved_type",
                    message="Cannot resolve type '.test.resolver.Missing' in 'consumer.proto'",
                    span=SourceSpan(file_path="consumer.proto", line=1),
                )
            ],
        )
        self.assertIsInstance(field.data_type, QualifiedName)

    def test_res_08_resolves_same_short_names_using_the_exact_fqn(self) -> None:
        nested_target = _struct("Target", "test.resolver.Owner")
        package_target = _struct("Target", "test.resolver")
        owner = _struct("Owner", "test.resolver")
        field = DataTypeField(
            name=Identifier("target"),
            data_type=_qualified_name(package_target.fully_qualified_name),
            field_number=1,
        )
        owner.fields = (field,)
        unresolved = _unresolved_reference(
            protobuf_type_name=".test.resolver.Owner.Target",
            field=field,
            owner_definition_key=owner.fully_qualified_name,
            kind=ReferenceTargetKind.FIELD_DATA_TYPE,
        )

        issues = resolve_references(
            [unresolved],
            {
                nested_target.fully_qualified_name: nested_target,
                package_target.fully_qualified_name: package_target,
                owner.fully_qualified_name: owner,
            },
        )

        self.assertEqual(issues, [])
        self.assertIs(field.data_type, nested_target)

    def test_res_09_reports_a_missing_fully_qualified_definition(self) -> None:
        owner = _struct("Owner", "test.resolver")
        field = DataTypeField(
            name=Identifier("target"),
            data_type=_qualified_name("test.resolver.Target"),
            field_number=1,
        )
        owner.fields = (field,)
        unresolved = _unresolved_reference(
            protobuf_type_name=".test.resolver.Target",
            field=field,
            owner_definition_key=owner.fully_qualified_name,
            kind=ReferenceTargetKind.FIELD_DATA_TYPE,
        )

        issues = resolve_references(
            [unresolved],
            {owner.fully_qualified_name: owner},
        )

        self.assertEqual([issue.code for issue in issues], ["unresolved_type"])
        self.assertIn(".test.resolver.Target", issues[0].message)
        self.assertIsInstance(field.data_type, QualifiedName)

    def test_res_10_reports_invalid_array_and_map_targets_without_mutating_fields(self) -> None:
        target = _struct("Target", "test.resolver")
        owner = _struct("Owner", "test.resolver")
        array_field = DataTypeField(
            name=Identifier("target"),
            data_type=_qualified_name(target.fully_qualified_name),
            field_number=1,
        )
        map_field = DataTypeField(
            name=Identifier("targets"),
            data_type=_qualified_name(target.fully_qualified_name),
            field_number=2,
        )
        owner.fields = (array_field, map_field)
        invalid_array_reference = _unresolved_reference(
            protobuf_type_name=".test.resolver.Target",
            field=array_field,
            owner_definition_key=owner.fully_qualified_name,
            kind=ReferenceTargetKind.ARRAY_ELEMENT_TYPE,
        )
        invalid_map_reference = _unresolved_reference(
            protobuf_type_name=".test.resolver.Target",
            field=map_field,
            owner_definition_key=owner.fully_qualified_name,
            kind=ReferenceTargetKind.MAP_VALUE_TYPE,
        )

        issues = resolve_references(
            [invalid_array_reference, invalid_map_reference],
            {
                owner.fully_qualified_name: owner,
                target.fully_qualified_name: target,
            },
        )

        self.assertEqual(
            [issue.code for issue in issues],
            ["unresolved_reference_target_invalid", "unresolved_reference_target_invalid"],
        )
        self.assertIn("not an array", issues[0].message)
        self.assertIn("not a map", issues[1].message)
        self.assertIsInstance(array_field.data_type, QualifiedName)
        self.assertIsInstance(map_field.data_type, QualifiedName)

    def test_res_11_resolves_valid_references_while_reporting_invalid_ones(self) -> None:
        target = _struct("Target", "test.resolver")
        owner = _struct("Owner", "test.resolver")
        valid_field = DataTypeField(
            name=Identifier("target"),
            data_type=_qualified_name(target.fully_qualified_name),
            field_number=1,
        )
        missing_field = DataTypeField(
            name=Identifier("missing"),
            data_type=_qualified_name("test.resolver.Missing"),
            field_number=2,
        )
        owner.fields = (valid_field, missing_field)
        valid_reference = _unresolved_reference(
            protobuf_type_name=".test.resolver.Target",
            field=valid_field,
            owner_definition_key=owner.fully_qualified_name,
            kind=ReferenceTargetKind.FIELD_DATA_TYPE,
        )
        missing_reference = _unresolved_reference(
            protobuf_type_name=".test.resolver.Missing",
            field=missing_field,
            owner_definition_key=owner.fully_qualified_name,
            kind=ReferenceTargetKind.FIELD_DATA_TYPE,
        )

        definitions_by_key = {
            target.fully_qualified_name: target,
            owner.fully_qualified_name: owner,
        }

        issues = resolve_references(
            [valid_reference, missing_reference],
            definitions_by_key,
        )

        self.assertEqual([issue.code for issue in issues], ["unresolved_type"])
        self.assertIs(valid_field.data_type, target)
        self.assertIsInstance(missing_field.data_type, QualifiedName)
        additional = _struct("Additional", "test.resolver")
        definitions_by_key[additional.fully_qualified_name] = additional
        self.assertIs(definitions_by_key[additional.fully_qualified_name], additional)


if __name__ == "__main__":
    unittest.main()
