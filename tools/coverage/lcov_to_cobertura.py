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

"""Convert Bazel's combined lcov coverage report into Cobertura XML.

GitHub Code Quality only ingests Cobertura XML, while `bazel coverage` can only
emit lcov (`--combined_report=lcov`).
"""

import argparse
import os
import sys
from pathlib import Path

from lcov_cobertura import LcovCobertura

# Relative to the workspace root; `bazel-out` is the convenience symlink Bazel
# creates there, so no `bazel info` call is needed.
DEFAULT_LCOV_REPORT = Path("bazel-out/_coverage/_coverage_report.dat")
DEFAULT_OUTPUT = Path("coverage.xml")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lcov-report", type=Path, default=DEFAULT_LCOV_REPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    # Under `bazel run` the process starts in the runfiles tree, not the workspace.
    workspace = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
    if workspace:
        os.chdir(workspace)

    if not args.lcov_report.exists():
        parser.error(f"{args.lcov_report} not found. Run `bazel coverage //score/...` first.")

    xml = LcovCobertura(args.lcov_report.read_text(encoding="utf-8")).convert()
    args.output.write_text(xml, encoding="utf-8")
    print(f"Wrote Cobertura report to {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
