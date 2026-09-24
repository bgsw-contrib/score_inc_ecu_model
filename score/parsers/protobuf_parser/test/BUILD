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

load("@rules_python//python:defs.bzl", "py_test")

package(default_visibility = ["//visibility:public"])

py_test(
    name = "protobuf_common_unit_test",
    srcs = ["common_test.py"],
    main = "common_test.py",
    deps = [
        "//score/parsers/protobuf_parser",
    ],
)

py_test(
    name = "protobuf_option_decoder_unit_test",
    srcs = [
        "option_decoder_test.py",
        "test_data/option_decoder_test_data.py",
    ],
    main = "option_decoder_test.py",
    deps = [
        "//score/parsers/protobuf_parser",
        "@com_google_protobuf//:protobuf_python",
    ],
)

py_test(
    name = "protobuf_parser_descriptor_unit_test",
    srcs = [
        "parser_descriptor_test.py",
        "test_data/parser_descriptor_test_data.py",
    ],
    main = "parser_descriptor_test.py",
    deps = [
        "//score/ecu_model/data_types",
        "//score/parsers/protobuf_parser",
        "@com_google_protobuf//:protobuf_python",
    ],
)

py_test(
    name = "protobuf_resolver_unit_test",
    srcs = ["resolver_test.py"],
    main = "resolver_test.py",
    deps = [
        "//score/ecu_model/data_types",
        "//score/parsers/protobuf_parser",
    ],
)

py_test(
    name = "protobuf_api_integration_test",
    srcs = ["api_test.py"],
    main = "api_test.py",
    deps = [
        "//score/parsers/protobuf_parser",
        "@com_google_protobuf//:protobuf_python",
    ],
)
