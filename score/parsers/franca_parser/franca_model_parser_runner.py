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

"""Bazel action entry point for producing a Franca model registry pickle."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from score.ecu_model.model import ModelRegistry
from score.parsers.franca_parser.parser import FrancaParser
from score.parsers.franca_parser.transformer.file_graph_transformer import (
    FrancaFileGraphTransformer,
)


def main(arguments: Sequence[str] | None = None) -> None:
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument("--src", action="append", required=True)
    argument_parser.add_argument("--dep", action="append", default=[])
    argument_parser.add_argument("--output", required=True)
    argument_parser.add_argument("--defined", action="append", default=[])
    argument_parser.add_argument("--need-preprocessor", action="store_true")
    parsed_arguments = argument_parser.parse_args(arguments)

    parser = FrancaParser(
        root_files=[Path(source) for source in parsed_arguments.src],
        dependency_files=[Path(dependency) for dependency in parsed_arguments.dep],
        defined=parsed_arguments.defined,
        need_preprocessor=parsed_arguments.need_preprocessor,
    )
    FrancaFileGraphTransformer(parser.parse_files()).transform_files()

    output_path = Path(parsed_arguments.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(ModelRegistry.serialize())


if __name__ == "__main__":
    main()
