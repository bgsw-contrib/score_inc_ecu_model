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

load("@rules_python//python:defs.bzl", "py_binary", "py_library")

package(default_visibility = ["//visibility:public"])

exports_files(
    ["run_load_and_merge.py"],
    visibility = ["//score/parsers/runner/test:__subpackages__"],
)

py_library(
    name = "load_and_merge",
    srcs = ["load_and_merge.py"],
    deps = [
        "//score/ecu_model",
        "//score/ecu_model/architecture",
        "//score/ecu_model/communication",
        "//score/ecu_model/data_types",
    ],
)

py_binary(
    name = "run_load_and_merge",
    srcs = ["run_load_and_merge.py"],
    main = "run_load_and_merge.py",
    deps = [
        ":load_and_merge",
        "//score/ecu_model",
        "@pypi//pydantic",
    ],
)
