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

"""Test shared protobuf parser contracts and naming helpers."""

from __future__ import annotations

import unittest

from score.parsers.protobuf_parser.common import (
    ProtoTransformerError,
    SourceSpan,
    TransformResult,
    package_parts,
    protobuf_fqn,
    protobuf_reference,
    qualified_name,
    require_name,
)


class ProtobufCommonUnitTest(unittest.TestCase):
    """Test common contracts without parser or resolver indirection."""

    def test_com_01_shared_result_and_issue_contract(self) -> None:
        self.assertEqual(SourceSpan(file_path="schema.proto", line=7).column, 1)

        unresolved_references = [object()]

        definitions_by_key = {}
        result = TransformResult(
            definitions_by_key=definitions_by_key,
            unresolved_references=unresolved_references,
        )
        self.assertIs(result.definitions_by_key, definitions_by_key)
        self.assertIs(result.unresolved_references, unresolved_references)

    def test_com_02_qualified_name_returns_a_score_qualified_name(self) -> None:
        self.assertEqual(qualified_name(()).as_str, "")
        self.assertEqual(
            qualified_name(("example", "deployment")).as_str,
            "example.deployment",
        )

    def test_com_03_protobuf_fqn_joins_components_and_rejects_empty_name(self) -> None:
        self.assertEqual(protobuf_fqn(("example", "Message")), "example.Message")

        with self.assertRaisesRegex(
            ProtoTransformerError,
            "A protobuf declaration must have a non-empty name",
        ):
            protobuf_fqn(())

    def test_com_04_package_parts_accepts_valid_packages_and_rejects_invalid_segments(self) -> None:
        self.assertEqual(package_parts("", "schema.proto"), ())
        self.assertEqual(
            package_parts("example.deployment", "schema.proto"),
            ("example", "deployment"),
        )

        for package in ("example..deployment", "example.bad-segment"):
            with self.subTest(package=package):
                with self.assertRaisesRegex(
                    ProtoTransformerError,
                    "schema.proto: malformed protobuf package",
                ):
                    package_parts(package, "schema.proto")

    def test_com_05_require_name_returns_name_and_reports_missing_descriptor_name(self) -> None:
        self.assertEqual(
            require_name(
                "Payload",
                file_path="schema.proto",
                descriptor_kind="message descriptor",
            ),
            "Payload",
        )

        with self.assertRaisesRegex(
            ProtoTransformerError,
            "schema.proto: enum descriptor has no name",
        ):
            require_name("", file_path="schema.proto", descriptor_kind="enum descriptor")

    def test_com_06_protobuf_reference_normalizes_leading_dot_and_rejects_invalid_names(self) -> None:
        self.assertEqual(
            protobuf_reference(".example.deployment.Payload", file_path="schema.proto").as_str,
            "example.deployment.Payload",
        )

        with self.assertRaisesRegex(
            ProtoTransformerError,
            "schema.proto: field type has no protobuf type name",
        ):
            protobuf_reference(".", file_path="schema.proto")
        with self.assertRaisesRegex(
            ProtoTransformerError,
            "schema.proto: malformed protobuf type name 'example.bad-name'",
        ):
            protobuf_reference("example.bad-name", file_path="schema.proto")


if __name__ == "__main__":
    unittest.main()
