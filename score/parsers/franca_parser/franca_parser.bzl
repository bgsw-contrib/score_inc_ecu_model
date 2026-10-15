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

"""Bazel rule for parsing Franca source targets into model registry pickles."""

def _franca_parse_impl(ctx):
    output = ctx.actions.declare_file(ctx.label.name + ".pkl")

    args = ctx.actions.args()
    args.add_all(ctx.files.srcs, before_each = "--src")
    args.add_all(ctx.files.deps, before_each = "--dep")
    args.add_all(ctx.attr.defined, before_each = "--defined")
    if ctx.attr.need_preprocessor:
        args.add("--need-preprocessor")
    args.add("--output", output)

    ctx.actions.run(
        executable = ctx.executable._parser_runner,
        inputs = ctx.files.srcs + ctx.files.deps,
        outputs = [output],
        arguments = [args],
        mnemonic = "FrancaModelParser",
        progress_message = "Parsing Franca model for %{label}",
    )

    return [DefaultInfo(files = depset([output]))]

_franca_parse = rule(
    implementation = _franca_parse_impl,
    attrs = {
        "defined": attr.string_list(),
        "deps": attr.label_list(allow_files = [".fidl", ".fdepl"]),
        "need_preprocessor": attr.bool(default = False),
        "srcs": attr.label_list(allow_files = [".fidl", ".fdepl"], mandatory = True),
        "_parser_runner": attr.label(
            default = Label("//score/parsers/franca_parser:franca_model_parser_runner"),
            cfg = "exec",
            executable = True,
        ),
    },
)

def franca_parse(name, srcs, deps = [], defined = [], need_preprocessor = False, **kwargs):
    """Create a Franca parsing action whose default output is a registry pickle."""
    _franca_parse(
        name = name,
        srcs = srcs,
        deps = deps,
        defined = defined,
        need_preprocessor = need_preprocessor,
        **kwargs
    )
