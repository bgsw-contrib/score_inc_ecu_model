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

"""Integration tests for FDEPL type-collection use resolution."""

import unittest
from pathlib import Path

from score.parsers.franca_parser.parser import FrancaParser
from score.parsers.franca_parser.transformer.file_graph_transformer import (
    FrancaFileGraphTransformer,
)

TEST_DATA_DIRECTORY = Path(__file__).parent / "test_data"


class ResolveUseTypeCollectionTest(unittest.TestCase):
    """Verify type-collection deployment use references across FDEPL files."""

    def test_transform_files_given_local_use_references_expect_referenced_deployments(self) -> None:
        fixture_directory = TEST_DATA_DIRECTORY / "resolve_local"
        root_file = fixture_directory / "local_use.fdepl"

        transformed_files = FrancaFileGraphTransformer(
            FrancaParser(
                root_files=[root_file],
                dependency_files=[
                    fixture_directory / "resolve_use_specification.fdepl",
                    fixture_directory / "resolve_use_types.fidl",
                ],
            ).parse_files()
        ).transform_files()

        deployments = transformed_files[root_file.resolve()].type_collection_deployments
        reusable_by_name = {deployment.name.as_str: deployment for deployment in deployments}

        for consumer_name in (
            "Consumer.Short",
            "Consumer.Partial",
            "Consumer.Full",
            "Consumer.Overlap",
        ):
            self.assertIs(
                reusable_by_name[consumer_name].use_definitions[0],
                reusable_by_name["Reusable.Deployment"],
            )
        self.assertIs(
            reusable_by_name["Consumer.SingleSegment"].use_definitions[0],
            reusable_by_name["Reusable"],
        )

    def test_transform_files_given_imported_use_reference_expect_referenced_deployment(self) -> None:
        fixture_directory = TEST_DATA_DIRECTORY / "resolve_imported"
        root_filenames = (
            "imported_use.fdepl",
            "imported_use_file_only.fdepl",
            "imported_use_fqn.fdepl",
            "imported_use_fqn_overlap.fdepl",
            "imported_use_fqn_partial.fdepl",
            "imported_use_overlap.fdepl",
            "imported_use_partial.fdepl",
            "imported_use_short.fdepl",
        )

        transformed_files = FrancaFileGraphTransformer(
            FrancaParser(
                root_files=[fixture_directory / filename for filename in root_filenames],
                dependency_files=[
                    fixture_directory / "imported_definition.fdepl",
                    fixture_directory / "imported_definition_fqn.fdepl",
                    fixture_directory / "resolve_use_specification.fdepl",
                    fixture_directory / "resolve_use_types.fidl",
                ],
            ).parse_files()
        ).transform_files()

        simple_deployment = transformed_files[
            (fixture_directory / "imported_definition.fdepl").resolve()
        ].type_collection_deployments[0]
        fqn_deployment = transformed_files[
            (fixture_directory / "imported_definition_fqn.fdepl").resolve()
        ].type_collection_deployments[0]
        expected_deployments = {
            "imported_use.fdepl": simple_deployment,
            "imported_use_file_only.fdepl": simple_deployment,
            "imported_use_fqn.fdepl": fqn_deployment,
            "imported_use_fqn_overlap.fdepl": fqn_deployment,
            "imported_use_fqn_partial.fdepl": fqn_deployment,
            "imported_use_overlap.fdepl": simple_deployment,
            "imported_use_partial.fdepl": simple_deployment,
            "imported_use_short.fdepl": simple_deployment,
        }

        for filename, expected_deployment in expected_deployments.items():
            actual_deployments = transformed_files[(fixture_directory / filename).resolve()]
            for deployment in actual_deployments.type_collection_deployments:
                self.assertTrue(deployment.use_definitions)
                self.assertTrue(all(definition is expected_deployment for definition in deployment.use_definitions))

    def test_transform_files_given_circular_import_use_reference_expect_referenced_deployment(self) -> None:
        fixture_directory = TEST_DATA_DIRECTORY / "resolve_circular_import"
        left_file = fixture_directory / "circular_left.fdepl"
        right_file = fixture_directory / "circular_right.fdepl"

        transformed_files = FrancaFileGraphTransformer(
            FrancaParser(
                root_files=[left_file],
                dependency_files=[
                    right_file,
                    fixture_directory / "resolve_use_specification.fdepl",
                    fixture_directory / "resolve_use_types.fidl",
                ],
            ).parse_files()
        ).transform_files()

        left_deployment = transformed_files[left_file.resolve()].type_collection_deployments[0]
        right_deployment = transformed_files[right_file.resolve()].type_collection_deployments[0]

        self.assertIs(left_deployment.use_definitions[0], right_deployment)
        self.assertIs(right_deployment.use_definitions[0], left_deployment)


if __name__ == "__main__":
    unittest.main()
