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

"""Integration tests for FDEPL deployment specification transformation."""

import unittest
from pathlib import Path

from score.parsers.franca_parser.model.fdepl.specification import (
    DeploymentPropertyType,
    PropertyFlag,
)
from score.parsers.franca_parser.parser import FrancaParser
from score.parsers.franca_parser.transformer.file_graph_transformer import (
    FrancaFileGraphTransformer,
)

SPECIFICATION_DIRECTORY = Path(__file__).parents[3] / "spec_files"


class FDEPLSpecificationTransformerTest(unittest.TestCase):
    """Verify specification declarations from the IPC fixture graph."""

    def test_transform_files_given_architecture_and_ipc_specs_expect_inherited_typed_properties(self) -> None:
        architecture_file = SPECIFICATION_DIRECTORY / "score_architecture_deployment_spec.fdepl"
        ipc_file = SPECIFICATION_DIRECTORY / "score_network_IPC_deployment_spec.fdepl"
        parser = FrancaParser(root_files=[ipc_file], dependency_files=[architecture_file])

        parsed_files = parser.parse_files()
        self.assertEqual(
            parsed_files[ipc_file.resolve()].imports[0].file_path,
            architecture_file.resolve(),
        )
        transformed_files = FrancaFileGraphTransformer(parsed_files).transform_files()

        architecture = transformed_files[architecture_file.resolve()].specifications[0]
        ipc = transformed_files[ipc_file.resolve()].specifications[0]
        self.assertEqual(architecture.name.as_str, "architecture")
        self.assertEqual(
            architecture.hosts["devices"]["ScoreProperty065"].type_reference.property_type, DeploymentPropertyType.ENUM
        )
        self.assertTrue(architecture.hosts["devices"]["ScoreProperty065"].type_reference.is_array)
        self.assertEqual(ipc.name.as_str, "ipc")
        self.assertIs(ipc.base_specifications[0], architecture)
        self.assertEqual(
            ipc.hosts["interfaces"]["ScoreProperty260"].liabilities[0].default_value.as_str, "ScoreValue013"
        )
        self.assertEqual(ipc.hosts["provided_ports"]["ScoreProperty252"].liabilities, [])
        self.assertEqual(
            ipc.hosts["broadcasts"]["ScoreProperty510"].type_reference.property_type, DeploymentPropertyType.INTEGER
        )
        self.assertTrue(ipc.hosts["broadcasts"]["ScoreProperty510"].type_reference.is_array)
        self.assertEqual(
            ipc.hosts["broadcasts"]["ScoreProperty250"].liabilities[0].property_flag, PropertyFlag.OPTIONAL
        )


if __name__ == "__main__":
    unittest.main()
