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

"""Integration tests for FIDL datatype declaration transformation."""

from pathlib import Path
import unittest

from lark.exceptions import VisitError

from score.ecu_model.data_types.array import ArrayDataType
from score.ecu_model.data_types.common import DataTypeSource
from score.ecu_model.data_types.enum import EnumDataType
from score.ecu_model.data_types.map import MapDataType
from score.ecu_model.data_types.primitives import PrimitiveDataType
from score.ecu_model.data_types.struct import StructDataType
from score.ecu_model.data_types.typedef import TypedefDataType
from score.parsers.franca_parser.parser import FrancaParser
from score.parsers.franca_parser.transformer.file_graph_transformer import FrancaFileGraphTransformer


TEST_DATA_DIRECTORY = Path(__file__).parent / "test_data" / "datatype_definitions"
REFERENCE_DATA_DIRECTORY = Path(__file__).parent / "test_data" / "reference_resolution"


class FIDLDatatypeTransformerTest(unittest.TestCase):
    """Verify FIDL datatype declarations transform into Orion models."""

    def test_transform_files_given_datatype_declarations_expect_models_and_metadata(self) -> None:
        # Given a FIDL type collection containing each supported datatype declaration.
        source_file = TEST_DATA_DIRECTORY / "datatype_definitions.fidl"
        parser = FrancaParser(root_files=[source_file], dependency_files=[])

        # When the parser transforms the source through the FIDL file graph.
        transformed_file = FrancaFileGraphTransformer(parser.parse_files()).transform_files()[source_file.resolve()]

        # Then declarations retain their source ordering, metadata, and datatype semantics.
        self.assertEqual(len(transformed_file.type_collections), 1)
        collection = transformed_file.type_collections[0]
        self.assertEqual(collection.name.as_str, "Definitions")
        self.assertEqual(
            [datatype.name.as_str for datatype in collection.datatypes],
            [
                "Speed",
                "Mode",
                "Payload",
                "Value",
                "UnboundedArray",
                "MaximumBoundedArray",
                "OpenLowerBoundedArray",
                "BoundedArray",
                "Lookup",
            ],
        )
        self.assertTrue(
            all(datatype.namespace.as_str == "example.datatypes.Definitions" for datatype in collection.datatypes)
        )
        self.assertTrue(all(datatype.source_kind is DataTypeSource.FRANCA for datatype in collection.datatypes))
        self.assertTrue(all(datatype.source_uri == str(source_file.resolve()) for datatype in collection.datatypes))

        typedef = collection.datatypes[0]
        enum = collection.datatypes[1]
        struct = collection.datatypes[2]
        unbounded_array = collection.datatypes[4]
        open_lower_bounded_array = collection.datatypes[6]
        bounded_array = collection.datatypes[7]
        datatype_map = collection.datatypes[8]

        self.assertIsInstance(typedef, TypedefDataType)
        self.assertIs(typedef.data_type, PrimitiveDataType.UINT32)
        self.assertIsInstance(enum, EnumDataType)
        self.assertEqual(
            [value.value for value in enum.values],
            [0, 5, 6, 16, 17, -2],
        )
        self.assertIsInstance(struct, StructDataType)
        self.assertIsInstance(struct.fields[1].data_type, ArrayDataType)
        self.assertTrue(struct.fields[1].data_type.is_inline)
        self.assertEqual(struct.fields[1].data_type.dimension_min, None)
        self.assertEqual(struct.fields[1].data_type.dimension_max, 8)
        self.assertIsInstance(unbounded_array, ArrayDataType)
        self.assertEqual((unbounded_array.dimension_min, unbounded_array.dimension_max), (None, None))
        self.assertEqual(
            (open_lower_bounded_array.dimension_min, open_lower_bounded_array.dimension_max),
            (None, 64),
        )
        self.assertEqual((bounded_array.dimension_min, bounded_array.dimension_max), (1, 64))
        self.assertIsInstance(datatype_map, MapDataType)
        self.assertIsInstance(datatype_map.key_type, PrimitiveDataType)
        self.assertIs(datatype_map.value_type, struct)

    def test_transform_files_given_file_imports_expect_imported_and_local_references_resolved(self) -> None:
        # Given a FIDL file importing named and anonymous type collections.
        root_file = REFERENCE_DATA_DIRECTORY / "file_only_root.fidl"
        shared_file = REFERENCE_DATA_DIRECTORY / "shared_types.fidl"
        anonymous_file = REFERENCE_DATA_DIRECTORY / "anonymous_types.fidl"
        parser = FrancaParser(
            root_files=[root_file],
            dependency_files=[shared_file, anonymous_file],
        )

        # When imports are transformed before the root file.
        transformed_files = FrancaFileGraphTransformer(parser.parse_files()).transform_files()

        # Then references bind to their declared imported or local datatype models.
        root_types = transformed_files[root_file.resolve()].type_collections[0]
        shared_types = transformed_files[shared_file.resolve()].type_collections[0]
        anonymous_types = transformed_files[anonymous_file.resolve()].type_collections[0]
        payload_alias, local_container, local_item = root_types.datatypes
        shared_payload = shared_types.datatypes[0]
        anonymous_payload = anonymous_types.datatypes[0]

        self.assertIs(payload_alias.data_type, shared_payload)
        self.assertIs(local_container.fields[0].data_type, local_item)
        self.assertIs(local_container.fields[1].data_type, shared_payload)
        self.assertIs(local_container.fields[2].data_type, shared_payload)
        self.assertIs(local_container.fields[3].data_type, anonymous_payload)
        self.assertIs(local_container.fields[4].data_type, anonymous_payload)

    def test_transform_files_given_local_type_collections_expect_same_and_sibling_references_resolved(self) -> None:
        # Given one FIDL file with references to declarations in two type collections.
        source_file = REFERENCE_DATA_DIRECTORY / "local_type_collections.fidl"
        parser = FrancaParser(root_files=[source_file], dependency_files=[])

        # When the FIDL model root resolves references still pending after import lookup.
        transformed_file = FrancaFileGraphTransformer(parser.parse_files()).transform_files()[source_file.resolve()]

        # Then declarations in the same and sibling collections resolve within the file.
        primary_types, secondary_types = transformed_file.type_collections
        primary_payload, local_references = primary_types.datatypes
        secondary_payload = secondary_types.datatypes[0]
        self.assertIs(local_references.fields[0].data_type, primary_payload)
        self.assertIs(local_references.fields[1].data_type, secondary_payload)

    def test_transform_files_given_duplicate_named_type_collections_expect_error(self) -> None:
        # Given a FIDL file with duplicate named type collections.
        source_file = REFERENCE_DATA_DIRECTORY / "duplicate_type_collections.fidl"
        parser = FrancaParser(root_files=[source_file], dependency_files=[])

        # When the FIDL model root validates top-level declaration names.
        with self.assertRaisesRegex(VisitError, "Duplicate TypeCollection ID SharedTypes"):
            FrancaFileGraphTransformer(parser.parse_files()).transform_files()

    def test_transform_files_given_circular_imports_expect_pending_references_resolved(self) -> None:
        # Given two FIDL files whose struct fields reference one another through imports.
        left_file = REFERENCE_DATA_DIRECTORY / "circular_left.fidl"
        right_file = REFERENCE_DATA_DIRECTORY / "circular_right.fidl"
        parser = FrancaParser(root_files=[left_file], dependency_files=[right_file])

        # When import traversal completes both declarations before final pending resolution.
        transformed_files = FrancaFileGraphTransformer(parser.parse_files()).transform_files()

        # Then the reference deferred while the cycle was open is bound to the left declaration.
        left_payload = transformed_files[left_file.resolve()].type_collections[0].datatypes[0]
        right_payload = transformed_files[right_file.resolve()].type_collections[0].datatypes[0]
        self.assertIs(left_payload.fields[0].data_type, right_payload)
        self.assertIs(right_payload.fields[0].data_type, left_payload)


if __name__ == "__main__":
    unittest.main()
