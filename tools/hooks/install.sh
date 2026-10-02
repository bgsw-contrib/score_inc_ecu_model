#!/usr/bin/env bash
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
#
# Symlinks every hook in .githooks/ into the repository's hook directory.
#
# Symlinks rather than core.hooksPath, which would make git ignore .git/hooks
# entirely and silently disable hooks installed by other tools.

set -euo pipefail
shopt -s nullglob

root="${BUILD_WORKSPACE_DIRECTORY:?run this with bazel run //:install_hooks}"
hooks_dir="$(git -C "$root" rev-parse --absolute-git-dir)/hooks"

mkdir -p "$hooks_dir"

for hook in "$root"/.githooks/*; do
    name="$(basename "$hook")"
    installed="$hooks_dir/$name"

    if [[ -L "$installed" && "$(readlink -f "$installed")" == "$(readlink -f "$hook")" ]]; then
        echo "$name: already installed"
        continue
    fi

    if [[ -e "$installed" || -L "$installed" ]]; then
        echo "$name: $installed already exists and points somewhere else." >&2
        echo "Remove or rename it, then run this again." >&2
        exit 1
    fi

    ln -s "$hook" "$installed"
    echo "$name: installed"
done
