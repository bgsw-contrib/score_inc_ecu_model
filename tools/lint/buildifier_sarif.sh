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
# Runs Buildifier recursively over the repository and converts its findings
# into a single SARIF report.

set -euo pipefail

root="${1:?repository root is required}"
output="${2:?SARIF output path is required}"
json_output="$(mktemp)"
hunks_output="$(mktemp)"
trap 'rm -f "$json_output" "$hunks_output"' EXIT

set +e
bazel run --ui_event_filters=,+error --noshow_progress -- \
    @buildifier_prebuilt//:buildifier \
    -r -mode=check -lint=warn -warnings=all -format=json "$root" >"$json_output"
buildifier_status=$?

# Code scanning only annotates changed lines, so point at the reformatted hunks.
bazel run --ui_event_filters=,+error --noshow_progress -- \
    @buildifier_prebuilt//:buildifier \
    -r -mode=diff -diff_command="diff -U0" "$root" 2>/dev/null |
    awk -v root="${root%/}/" '
        /^--- / {
            file = substr($0, 5)
            sub(/\t.*/, "", file)
            if (index(file, root) == 1) file = substr(file, length(root) + 1)
            next
        }
        /^@@ / {
            count = split(substr($2, 2), old, ",")
            start = old[1] + 0
            lines = (count > 1) ? old[2] + 0 : 1
            if (start < 1) start = 1
            end = (lines > 0) ? start + lines - 1 : start
            printf "%s\t%d\t%d\n", file, start, end
        }' |
    jq -R -s 'split("\n") | map(select(length > 0) | split("\t")
        | {file: .[0], start: (.[1] | tonumber), end: (.[2] | tonumber)})' >"$hunks_output"
set -e

jq --arg root "${root%/}/" --slurpfile hunks "$hunks_output" '
  def relative_path:
    sub("^" + $root; "");

  def region:
    {
      startLine: .start.line,
      startColumn: .start.column,
      endLine: .end.line,
      endColumn: .end.column
    };

  def location($file; $warning):
    {
      physicalLocation: {
        artifactLocation: {uri: ($file.filename | relative_path)},
        region: ($warning | region)
      }
    };

  {
    "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
    version: "2.1.0",
    runs: [{
      tool: {
        driver: {
          name: "Buildifier",
          informationUri: "https://github.com/bazelbuild/buildtools",
          rules: (
            ([.files[]?.warnings[]?.category] + ["buildifier-format"])
            | unique
            | map({id: .})
          )
        }
      },
      results: [
        (.files[] as $file
          | $file.warnings[]? as $warning
          | {
              ruleId: $warning.category,
              level: "warning",
              message: {text: $warning.message},
              locations: [location($file; $warning)]
            }),
        ($hunks[0][]
          | {
              ruleId: "buildifier-format",
              level: "error",
              message: {text: "Formatting differs from Buildifier output. Run `bazel run //:format` to fix it."},
              locations: [{
                physicalLocation: {
                  artifactLocation: {uri: .file},
                  region: {startLine: .start, endLine: .end}
                }
              }]
            })
      ]
    }]
  }
' "$json_output" >"$output"

if [[ "$(jq -r '.success // false' "$json_output")" != "true" ]]; then
  buildifier_status=1
fi

exit "$buildifier_status"
