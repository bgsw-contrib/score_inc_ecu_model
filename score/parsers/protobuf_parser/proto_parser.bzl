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

"""Bazel rule for parsing Protobuf targets into model registry pickles."""

load("@rules_proto//proto:defs.bzl", "ProtoInfo")

def _protobuf_parse_impl(ctx):
    descriptor_sets = []
    for protobuf_dep in ctx.attr.protobuf_deps:
        if ProtoInfo in protobuf_dep:
            descriptor_sets.extend(protobuf_dep[ProtoInfo].transitive_descriptor_sets.to_list())
        elif hasattr(protobuf_dep, "files"):
            descriptor_sets.extend(protobuf_dep.files.to_list())

    descriptor_by_path = {file.path: file for file in descriptor_sets}
    descriptor_sets = [descriptor_by_path[path] for path in sorted(descriptor_by_path)]
    output = ctx.actions.declare_file(ctx.label.name + ".pkl")

    args = ctx.actions.args()
    args.add_all(descriptor_sets, before_each = "--descriptor-set")
    args.add("--output", output)

    ctx.actions.run(
        executable = ctx.executable._parser_runner,
        inputs = descriptor_sets,
        outputs = [output],
        arguments = [args],
        mnemonic = "ProtobufModelParser",
        progress_message = "Parsing Protobuf model for %{label}",
    )

    return [DefaultInfo(files = depset([output]))]

_protobuf_parse = rule(
    implementation = _protobuf_parse_impl,
    attrs = {
        "protobuf_deps": attr.label_list(allow_files = True, mandatory = True),
        "_parser_runner": attr.label(
            default = Label("//score/parsers/protobuf_parser:protobuf_model_parser_runner"),
            cfg = "exec",
            executable = True,
        ),
    },
)

def protobuf_parse(name, protobuf_deps, **kwargs):
    """Create a Protobuf parsing action whose default output is a registry pickle."""
    _protobuf_parse(
        name = name,
        protobuf_deps = protobuf_deps,
        **kwargs
    )
