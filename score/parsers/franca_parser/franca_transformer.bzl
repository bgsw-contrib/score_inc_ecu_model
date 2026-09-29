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

"""Rules for transforming Franca FIDL files."""

def _franca_transformer_impl(ctx):
    args = ctx.actions.args()
    for source in ctx.files.srcs:
        args.add("--src", source.path)
    for dependency in ctx.files.deps:
        args.add("--dep", dependency.path)
    args.add("--out", ctx.outputs.transformed_franca_files.path)

    ctx.actions.run(
        inputs = ctx.files.srcs + ctx.files.deps,
        outputs = [ctx.outputs.transformed_franca_files],
        arguments = [args],
        executable = ctx.executable._runner,
        mnemonic = "FrancaTransformer",
        progress_message = "Transform Franca FIDL files {}".format(ctx.label),
    )
    return DefaultInfo(files = depset([ctx.outputs.transformed_franca_files]))

_franca_transformer = rule(
    implementation = _franca_transformer_impl,
    attrs = {
        "deps": attr.label_list(allow_files = [".fidl", ".fdepl"]),
        "srcs": attr.label_list(allow_files = [".fidl", ".fdepl"]),
        "transformed_franca_files": attr.output(mandatory = True),
        "_runner": attr.label(
            default = Label("//score/parsers/franca_parser:franca_transformer_runner"),
            cfg = "exec",
            executable = True,
        ),
    },
)

def franca_transformer(name, srcs, deps = [], **kwargs):
    _franca_transformer(
        name = name,
        srcs = srcs,
        deps = deps,
        transformed_franca_files = name + "_franca_parser/gen/" + name + "_transformed_franca_files.pkl",
        **kwargs
    )
