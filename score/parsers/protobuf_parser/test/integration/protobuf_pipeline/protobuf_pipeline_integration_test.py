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

"""Validate end-to-end Protobuf ingestion through the public parser API."""

from __future__ import annotations

import os
from pathlib import Path
import pickle
import unittest

from score.ecu_model.data_types.array import ArrayDataType
from score.ecu_model.data_types.enum import EnumDataType
from score.ecu_model.data_types.map import MapDataType
from score.ecu_model.data_types.primitives import PrimitiveDataType
from score.ecu_model.data_types.struct import StructDataType
from score.ecu_model.data_types.union import UnionDataType


class ProtobufPipelineIntegrationTest(unittest.TestCase):
    """Test successful end-to-end protobuf ingestion scenarios."""

    def test_resolves_nested_struct_and_enum_fields_from_another_message(self):
        registry = load_pipeline_registry()["datatypes"]

        nested_struct = registry.get("integration.pipeline.NestedTypeContainer.NestedPayload")
        nested_enum = registry.get("integration.pipeline.NestedTypeContainer.NestedState")
        top_level_enum = registry.get("integration.pipeline.TopLevelState")

        nested_type_consumer = registry.get("integration.pipeline.NestedTypeConsumer")
        self.assertIsInstance(nested_struct, StructDataType)
        self.assertIsInstance(nested_enum, EnumDataType)
        self.assertIsInstance(top_level_enum, EnumDataType)
        self.assertIsInstance(nested_type_consumer, StructDataType)
        fields = {field.name.as_str: field for field in nested_type_consumer.fields}
        self.assertIs(fields["payload"].data_type, nested_struct)
        self.assertIs(fields["state"].data_type, nested_enum)
        self.assertIs(fields["top_level_state"].data_type, top_level_enum)

    def test_returns_resolved_collections_and_oneof_models(self):
        registry = load_pipeline_registry()["datatypes"]
        shape = registry.get("integration.pipeline.collections.Shape")
        child = registry.get("integration.pipeline.collections.Child")
        state = registry.get("integration.pipeline.collections.State")
        external = registry.get("integration.pipeline.collections.External")
        external_entry = registry.get("integration.pipeline.collections.External.CountsEntry")

        self.assertIsInstance(shape, StructDataType)
        self.assertIsInstance(child, StructDataType)
        self.assertIsInstance(state, EnumDataType)
        self.assertIsInstance(external, StructDataType)
        self.assertIsInstance(external_entry, StructDataType)
        self.assertIs(external.nested_structs[0], external_entry)

        fields = {field.name.as_str: field for field in shape.fields}
        self.assertTrue(fields["nickname"].optional)
        self.assertIs(fields["nickname"].data_type, PrimitiveDataType.STRING)
        self.assertIsInstance(fields["counts"].data_type, MapDataType)
        self.assertIs(fields["counts"].data_type.key_type, PrimitiveDataType.STRING)
        self.assertIs(fields["counts"].data_type.value_type, child)

        identity = fields["identity"].data_type
        self.assertIsInstance(identity, UnionDataType)
        self.assertEqual([field.name.as_str for field in identity.fields], ["email", "child"])
        self.assertIs(identity.fields[1].data_type, child)
        self.assertIsInstance(fields["children"].data_type, ArrayDataType)
        self.assertIs(fields["children"].data_type.data_type, child)
        self.assertIs(fields["state"].data_type, state)
        self.assertIs(fields["external_entry"].data_type, external_entry)

    def test_resolves_cross_file_references_from_a_direct_import(self):
        registry = load_pipeline_registry()["datatypes"]

        payload = registry.get("integration.shared.Payload")
        request = registry.get("integration.consumer.Request")
        self.assertIsInstance(payload, StructDataType)
        self.assertIsInstance(request, StructDataType)
        fields = {field.name.as_str: field for field in request.fields}
        self.assertIs(fields["payload"].data_type, payload)
        self.assertIsInstance(fields["payloads"].data_type, ArrayDataType)
        self.assertIs(fields["payloads"].data_type.data_type, payload)
        self.assertIsInstance(fields["payloads_by_id"].data_type, MapDataType)
        self.assertIs(fields["payloads_by_id"].data_type.value_type, payload)
        alternative_payload = fields["alternative_payload"].data_type
        self.assertIsInstance(alternative_payload, UnionDataType)
        self.assertIs(alternative_payload.fields[0].data_type, payload)


def load_pipeline_registry():
    """Load the registry generated by the Bazel descriptor pipeline."""
    runfiles_root = Path(os.environ["RUNFILES_DIR"])
    output_path = next(runfiles_root.rglob("pipeline_model.pickle"))
    return pickle.loads(output_path.read_bytes())


if __name__ == "__main__":
    unittest.main()
