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

"""Bazel executable that forwards descriptor artifacts to ProtobufToDataTypeParser."""

from __future__ import annotations

import argparse
from pathlib import Path
import pickle
from typing import Sequence

from score.parsers.protobuf_parser.api import (
    ProtobufToDataTypeParser,
)


def main(arguments: Sequence[str] | None = None) -> None:
    """Parse descriptor artifacts and write the resulting registry as a pickle."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--descriptor-set", action="append", required=True)
    parser.add_argument("--output", required=True)
    parsed_arguments = parser.parse_args(arguments)

    registry = ProtobufToDataTypeParser.parse(parsed_arguments.descriptor_set)
    with Path(parsed_arguments.output).open("wb") as output_file:
        pickle.dump({"datatypes": registry}, output_file, protocol=pickle.HIGHEST_PROTOCOL)


if __name__ == "__main__":
    main()
