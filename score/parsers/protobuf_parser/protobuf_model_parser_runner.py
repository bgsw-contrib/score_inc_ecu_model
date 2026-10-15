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

"""Bazel action entry point for producing a Protobuf model registry pickle."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from score.ecu_model.model import ModelRegistry
from score.parsers.protobuf_parser.api import ProtobufToDataTypeParser


def main(arguments: Sequence[str] | None = None) -> None:
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument("--descriptor-set", action="append", required=True)
    argument_parser.add_argument("--output", required=True)
    parsed_arguments = argument_parser.parse_args(arguments)

    ProtobufToDataTypeParser.parse(parsed_arguments.descriptor_set)

    output_path = Path(parsed_arguments.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(ModelRegistry.serialize())


if __name__ == "__main__":
    main()
