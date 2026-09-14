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

"""Integration tests for legacy-compatible Franca datatype deployment properties."""

from pathlib import Path
import unittest

from score.ecu_model.data_types.array import ArrayDataType
from score.ecu_model.data_types.enum import EnumDataType
from score.ecu_model.data_types.struct import StructDataType
from score.ecu_model.data_types.typedef import TypedefDataType
from score.ecu_model.data_types.union import UnionDataType
from score.parsers.franca_parser.parser import FrancaParser
from score.parsers.franca_parser.transformer.file_graph_transformer import (
    FrancaFileGraphTransformer,
)


TEST_DATA_DIRECTORY = Path(__file__).parent / "test_data"


class DeploymentPropertyApplierTest(unittest.TestCase):
    """Verify deployment properties applied from transformed FDEPL definitions."""

    def test_apply_given_someip_datatype_deployments_expect_legacy_compatible_properties(self) -> None:
        deployment_file = TEST_DATA_DIRECTORY / "datatype_properties_deployment.fdepl"
        types_file = TEST_DATA_DIRECTORY / "datatype_properties.fidl"
        specification_file = TEST_DATA_DIRECTORY / "score_network_SOMEIP_deployment_spec.fdepl"
        architecture_file = TEST_DATA_DIRECTORY / "score_architecture_deployment_spec.fdepl"
        parser = FrancaParser(
            root_files=[deployment_file],
            dependency_files=[types_file, specification_file, architecture_file],
        )
        transformed_files = FrancaFileGraphTransformer(parser.parse_files()).transform_files()

        type_collection = transformed_files[types_file.resolve()].type_collections[0]
        datatypes_by_name = {datatype.name.as_str: datatype for datatype in type_collection.datatypes}
        message_text = datatypes_by_name["MessageText"]
        message = datatypes_by_name["Message"]
        payload = datatypes_by_name["Payload"]
        message_list = datatypes_by_name["MessageList"]
        status = datatypes_by_name["Status"]
        self.assertIsInstance(message_text, TypedefDataType)
        self.assertIsInstance(message, StructDataType)
        self.assertIsInstance(payload, UnionDataType)
        self.assertIsInstance(message_list, ArrayDataType)
        self.assertIsInstance(status, EnumDataType)

        self.assertEqual(
            message_text.deployment_properties,
            {"ScoreProperty481": 42, "ScoreProperty482": 42},
        )
        self.assertEqual(
            message.deployment_properties,
            {"ScoreProperty483": 42, "ScoreProperty493": False},
        )
        self.assertEqual(
            message.fields[0].deployment_properties,
            {
                "ScoreProperty481": 42,
                "ScoreProperty347": 42,
                "ScoreProperty346": 42,
                "ScoreProperty345": 42,
                "ScoreProperty482": 42,
            },
        )
        self.assertEqual(payload.deployment_properties, {"ScoreProperty484": True})
        self.assertEqual(
            message_list.deployment_properties,
            {
                "ScoreProperty347": 42,
                "ScoreProperty346": 42,
                "ScoreProperty345": 42,
                "ScoreProperty481": 42,
                "ScoreProperty482": 42,
            },
        )
        self.assertEqual(status.deployment_properties, {"ScoreProperty405": 42})


if __name__ == "__main__":
    unittest.main()
