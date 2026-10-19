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

"""Behavior tests for Franca file graph transformation."""

import os
import unittest
from pathlib import Path

from score.ecu_model.data_types.common import DataTypeBase
from score.ecu_model.data_types.struct import StructDataType
from score.ecu_model.model import ModelRegistry


class FrancaParserIntegrationTest(unittest.TestCase):
    """Verify Bazel parser actions produce the model-registry contract."""

    def load_datatypes(self, target_name: str) -> dict[str, DataTypeBase]:
        runfiles_root = Path(os.environ["RUNFILES_DIR"])
        output_path = next(runfiles_root.rglob(f"{target_name}.pkl"))
        ModelRegistry.deserialize(output_path.read_bytes())
        return {
            element.name.as_str: element
            for element in ModelRegistry.elements.values()
            if isinstance(element, DataTypeBase) and element.name is not None
        }

    def test_parse_files_given_import_expect_registered_resolved_models(self) -> None:
        datatypes = self.load_datatypes("franca_file_graph_model_registry")

        root_value = datatypes["RootValue"]
        imported_value = datatypes["ImportedValue"]
        self.assertIsInstance(root_value, StructDataType)
        self.assertIsInstance(imported_value, StructDataType)
        self.assertIs(root_value.fields[0].data_type, imported_value)

    def test_parse_files_given_defined_macro_expect_only_enabled_model(self) -> None:
        datatypes = self.load_datatypes("franca_preprocessor_model_registry")

        self.assertIn("FeatureValue", datatypes)
        self.assertNotIn("FallbackValue", datatypes)


if __name__ == "__main__":
    unittest.main()
