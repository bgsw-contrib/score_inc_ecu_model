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

"""Ruff aspects."""

load("@aspect_rules_lint//lint:ruff.bzl", "lint_ruff_aspect")

visibility(["//..."])

# Define the ruff linter aspect for Python targets. The repo's //:.ruff.toml
# is passed so the lint aspect and `ruff format` read the same config file.
ruff = lint_ruff_aspect(
    binary = Label("@aspect_rules_lint//lint:ruff_bin"),
    configs = [Label("//:.ruff.toml")],
)
