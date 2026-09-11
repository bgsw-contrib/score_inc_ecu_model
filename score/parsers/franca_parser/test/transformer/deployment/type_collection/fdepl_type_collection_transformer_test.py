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

"""Integration tests for FDEPL type-collection deployment transformation."""

from pathlib import Path
import unittest

from score.ecu_model.data_types.data_type_definition import (
    ArrayDataType,
    EnumDataType,
    EnumValue,
    MapDataType,
    StructDataType,
    TypedefDataType,
    UnionDataType,
)
from score.parsers.franca_parser.model.fdepl.type_collection_deployment import (
    ArrayDeployment,
    EnumValueDeployment,
    EnumerationDeployment,
    MapDeployment,
    StructDeployment,
    TypedefDeployment,
    UnionDeployment,
)
from score.parsers.franca_parser.parser import FrancaParser
from score.parsers.franca_parser.transformer.file_graph_transformer import (
    FrancaFileGraphTransformer,
)


TEST_DATA_DIRECTORY = Path(__file__).parent / "test_data"


class FDEPLTypeCollectionTransformerTest(unittest.TestCase):
    """Verify type-collection deployments from a self-contained FDEPL graph."""

    def test_transform_files_given_anonymous_type_collection_expect_target_bound_by_package(self) -> None:
        deployment_file = TEST_DATA_DIRECTORY / "anonymous_someip_deployment.fdepl"
        specification_file = TEST_DATA_DIRECTORY / "someip_deployment_spec.fdepl"
        types_file = TEST_DATA_DIRECTORY / "anonymous_types.fidl"
        parser = FrancaParser(
            root_files=[deployment_file],
            dependency_files=[specification_file, types_file],
        )

        transformed_files = FrancaFileGraphTransformer(parser.parse_files()).transform_files()

        deployment = transformed_files[deployment_file.resolve()].type_collection_deployments[0]
        self.assertIsNone(deployment.target.name)
        self.assertEqual(deployment.target.datatypes[0].name.as_str, "Payload")

    def test_transform_files_given_someip_type_collection_deployment_expect_bound_datatype_deployments(self) -> None:
        deployment_file = TEST_DATA_DIRECTORY / "score_type_collection_someip_deployment.fdepl"
        specification_file = TEST_DATA_DIRECTORY / "someip_deployment_spec.fdepl"
        types_file = TEST_DATA_DIRECTORY / "score_type_collection_types.fidl"
        parser = FrancaParser(
            root_files=[deployment_file],
            dependency_files=[specification_file, types_file],
        )

        transformed_files = FrancaFileGraphTransformer(parser.parse_files()).transform_files()

        deployment = transformed_files[deployment_file.resolve()].type_collection_deployments[0]
        self.assertEqual(deployment.specification.name.as_str, "someip")
        self.assertEqual(deployment.target.name.as_str, "TypeCollectionSkyLandmarks")
        self.assertEqual(deployment.name.as_str, "TypeCollectionSkyLandmarksSomeipStringDeployment_v1_0")
        self.assertEqual(len(deployment.deployment_elements), 6)

        struct_deployment = deployment.deployment_elements[0]
        self.assertIsInstance(struct_deployment, StructDeployment)
        self.assertIsInstance(struct_deployment.deployed_type, StructDataType)
        self.assertEqual(struct_deployment.deployed_type.name.as_str, "OCRText")
        self.assertEqual(
            [(parameter.name.as_str, parameter.value) for parameter in struct_deployment.parameter_set],
            [("SomeIpStructLength", 42)],
        )
        self.assertEqual(struct_deployment.fields[0].deployed_type.name.as_str, "Character")
        self.assertEqual(struct_deployment.fields[0].parameter_set[0].name.as_str, "ScoreProperty481")
        self.assertEqual(struct_deployment.fields[0].parameter_set[0].value, 42)
        self.assertNotIn(
            "SomeIpStructLength",
            struct_deployment.deployed_type.deployment_properties,
        )

        union_deployment = deployment.deployment_elements[1]
        self.assertIsInstance(union_deployment, UnionDeployment)
        self.assertIsInstance(union_deployment.deployed_type, UnionDataType)
        self.assertEqual(union_deployment.deployed_type.name.as_str, "Payload")
        self.assertEqual(
            [(parameter.name.as_str, parameter.value) for parameter in union_deployment.parameter_set],
            [("SomeIpUnionLength", 42)],
        )
        self.assertEqual(union_deployment.fields[0].deployed_type.name.as_str, "text")
        self.assertEqual(union_deployment.fields[0].parameter_set[0].name.as_str, "ScoreProperty481")
        self.assertEqual(union_deployment.fields[0].parameter_set[0].value, 42)

        typedef_deployment = deployment.deployment_elements[2]
        self.assertIsInstance(typedef_deployment, TypedefDeployment)
        self.assertIsInstance(typedef_deployment.deployed_type, TypedefDataType)
        self.assertEqual(typedef_deployment.deployed_type.name.as_str, "DisplayText")
        self.assertEqual(typedef_deployment.parameter_set[0].name.as_str, "ScoreProperty481")
        self.assertEqual(typedef_deployment.parameter_set[0].value, 42)

        array_deployment = deployment.deployment_elements[3]
        self.assertIsInstance(array_deployment, ArrayDeployment)
        self.assertIsInstance(array_deployment.deployed_type, ArrayDataType)
        self.assertEqual(array_deployment.deployed_type.name.as_str, "byteArray")
        self.assertEqual(
            [(parameter.name.as_str, parameter.value) for parameter in array_deployment.parameter_set],
            [("ScoreProperty247", 42), ("ScoreProperty246", 42)],
        )

        enumeration_deployment = deployment.deployment_elements[4]
        self.assertIsInstance(enumeration_deployment, EnumerationDeployment)
        self.assertIsInstance(enumeration_deployment.deployed_type, EnumDataType)
        self.assertEqual(enumeration_deployment.deployed_type.name.as_str, "SeverityEnum")
        self.assertEqual(enumeration_deployment.parameter_set[0].name.as_str, "ScoreProperty069")
        self.assertEqual(enumeration_deployment.parameter_set[0].value.as_str, "ScoreValue238")
        enum_value_deployment = enumeration_deployment.enumerators[0]
        self.assertIsInstance(enum_value_deployment, EnumValueDeployment)
        self.assertIsInstance(enum_value_deployment.deployed_type, EnumValue)
        self.assertEqual(enum_value_deployment.deployed_type.name.as_str, "Info")
        self.assertEqual(enum_value_deployment.parameter_set[0].name.as_str, "ScoreProperty074")
        self.assertEqual(enum_value_deployment.parameter_set[0].value.as_str, "ScoreValue102")

        map_deployment = deployment.deployment_elements[5]
        self.assertIsInstance(map_deployment, MapDeployment)
        self.assertIsInstance(map_deployment.deployed_type, MapDataType)
        self.assertEqual(map_deployment.deployed_type.name.as_str, "MetaInfoType")
        self.assertIsInstance(map_deployment.deployed_type.map_from, TypedefDataType)
        self.assertEqual(map_deployment.deployed_type.map_from.name.as_str, "DisplayText")
        self.assertEqual(
            [(parameter.name.as_str, parameter.value.as_str) for parameter in map_deployment.key],
            [("MapKeyParam", "MapKeyValue")],
        )
        self.assertEqual(
            [(parameter.name.as_str, parameter.value.as_str) for parameter in map_deployment.value],
            [("MapValueParam", "MapValValue")],
        )


if __name__ == "__main__":
    unittest.main()
