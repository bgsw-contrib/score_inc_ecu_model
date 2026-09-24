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

# Protobuf Parser Test Directory

This directory verifies the public SCORE Protobuf parser behavior from
serialized `FileDescriptorSet` artifacts. Tests create descriptors with
`google.protobuf.descriptor_pb2`, write them to temporary files, and exercise
the parser without a host compiler, `protoc`, source `.proto` files, runfiles,
or pickle artifacts.

## Test Scope

The five active targets cover the production boundary below:

```text
FileDescriptorSet artifacts
  -> DescriptorSetTransformer.transform()
  -> resolve_references()
  -> ProtobufToDataTypeParser.parse()
```

| Test file | Bazel target | Case-ID family | What it verifies |
| --- | --- | --- | --- |
| `common_test.py` | `protobuf_common_unit_test` | `COM` | Naming helpers and shared parser contracts. |
| `option_decoder_test.py` | `protobuf_option_decoder_unit_test` | `OPT` | Standard/custom options, flattened metadata, and option-pool errors. |
| `parser_descriptor_test.py` | `protobuf_parser_descriptor_unit_test` | `PAR` | Descriptor loading, model conversion, metadata, deferred references, and parser errors. |
| `resolver_test.py` | `protobuf_resolver_unit_test` | `RES` | Protobuf-name lookup, in-place reference binding, and resolver issues. |
| `api_test.py` | `protobuf_api_integration_test` | `API` | The public `ProtobufToDataTypeParser.parse()` dictionary and error contracts. |

Tests below `integration/` are deliberately outside this parser API target set.
They cover macro-backed behavior, not the artifact-based `ProtobufToDataTypeParser.parse()`
contract, and therefore have no `COM`/`OPT`/`PAR`/`RES`/`API` case IDs.

## Case-ID Naming

Each planned test function begins with the lower-case, underscore form of its
single case ID. For example, `test_com_01_...` implements `COM-01` and
`test_opt_03_...` implements `OPT-03`. Functions are physically ordered by
case number within each file, so a failing test maps directly to its row in the
case-ID sequence.

This convention makes a failing test directly traceable to the scenario table
without using a hyphen, which Python identifiers do not allow.

## Run Tests

Run commands from the `eclipse-score-inc_ecu_model` repository root:

```sh
bazel test \
  //score/parsers/protobuf_parser/test:protobuf_common_unit_test
bazel test \
  //score/parsers/protobuf_parser/test:protobuf_option_decoder_unit_test
bazel test \
  //score/parsers/protobuf_parser/test:protobuf_parser_descriptor_unit_test
bazel test \
  //score/parsers/protobuf_parser/test:protobuf_resolver_unit_test
bazel test \
  //score/parsers/protobuf_parser/test:protobuf_api_integration_test
```

For a fresh execution while investigating a failure, append
`--nocache_test_results --test_output=errors`.

## Adding a Case

1. Assign the next available ID in the relevant family.
2. Name the test `test_<family>_<number>_...` and keep one planned scenario per
  test function.
3. Build only official `descriptor_pb2` descriptors, serialize a
  `FileDescriptorSet` to a test-owned temporary path, and assert stable public
  model or issue data.
4. Keep compiler, source-import visibility, registry construction, macro
   outputs, and downstream generator behavior out of these five targets.
