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

"""Tests for Franca conditional preprocessing."""

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from score.parsers.franca_parser.preprocessor.preprocess import PreProcessError, main, parse_args, preprocess


class PreprocessTest(unittest.TestCase):
    """Verify directive selection, validation, and command-line file handling."""

    def test_preprocess_selects_if_elif_and_else_blocks(self) -> None:
        content = (
            "before\n#if defined FEATURE\nfeature\n#elif defined ALT\nalternative\n#else\nfallback\n#endif\nafter\n"
        )

        self.assertEqual(preprocess(content, {"FEATURE"}), "before\nfeature\nafter\n")
        self.assertEqual(preprocess(content, {"ALT"}), "before\nalternative\nafter\n")
        self.assertEqual(preprocess(content, set()), "before\nfallback\nafter\n")

    def test_preprocess_preserves_unrecognized_lines_and_empty_content(self) -> None:
        self.assertEqual(preprocess("#define FEATURE\nplain\n", set()), "#define FEATURE\nplain\n")
        self.assertEqual(preprocess("", set()), "")

    def test_preprocess_rejects_invalid_directive_order_and_nesting(self) -> None:
        invalid_inputs = (
            ("#if defined OUTER\n#if defined INNER\n#endif\n#endif\n", "Unsupported nested #if, line 2"),
            ("#elif defined FEATURE\n", "#elif without previous #if, line 1"),
            ("#else\n", "#else without previous #if, line 1"),
            ("#endif\n", "#endif without previous #if, line 1"),
            ("#if defined FEATURE\nbody\n", "Non terminated #if block"),
        )
        for content, error_message in invalid_inputs:
            with self.subTest(error_message=error_message), self.assertRaisesRegex(PreProcessError, error_message):
                preprocess(content, set())

    def test_parse_args_reads_repeated_defines_and_paths(self) -> None:
        with patch.object(
            sys,
            "argv",
            ["preprocess", "-D", "FEATURE", "-D", "ALT", "-o", "out.fidl", "-i", "in.fidl"],
        ):
            args = parse_args()

        self.assertEqual(args.defines, ["FEATURE", "ALT"])
        self.assertEqual(args.output, Path("out.fidl"))
        self.assertEqual(args.input_src, Path("in.fidl"))

    def test_parse_args_requires_input_source(self) -> None:
        with (
            patch.object(sys, "argv", ["preprocess", "-o", "out.fidl"]),
            self.assertRaises(SystemExit) as error_context,
        ):
            parse_args()

        self.assertEqual(error_context.exception.code, 2)

    def test_main_reads_source_and_writes_preprocessed_output(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            input_path = Path(temporary_directory) / "input.fidl"
            output_path = Path(temporary_directory) / "output.fidl"
            input_path.write_text("#if defined FEATURE\nselected\n#endif\n", encoding="utf-8")
            args = SimpleNamespace(defines=["FEATURE"], input_src=input_path, output=output_path)

            with patch(
                "score.parsers.franca_parser.preprocessor.preprocess.parse_args",
                return_value=args,
            ):
                main()

            self.assertEqual(output_path.read_text(encoding="utf-8"), "selected\n")


if __name__ == "__main__":
    unittest.main()
