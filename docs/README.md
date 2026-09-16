<!----
*******************************************************************************
Copyright (c) 2026 Contributors to the Eclipse Foundation

See the NOTICE file(s) distributed with this work for additional
information regarding copyright ownership.

This program and the accompanying materials are made available under the
terms of the Apache License Version 2.0 which is available at
https://www.apache.org/licenses/LICENSE-2.0

SPDX-License-Identifier: Apache-2.0
*******************************************************************************
-->

# EcuModel Documentation

[![Eclipse Score](https://img.shields.io/badge/Eclipse-Score-orange.svg)](https://eclipse-score.github.io/score/main/modules/communication/index.html)

User and developer documentation will be shared here in the future.

## Contents

- [ECU Model Reference](model_reference.md) — API documentation generated from
  the model sources. Regenerate it after changing classes, fields or docstrings:

  ```bash
  bazel run //tools/docgen:generate_model_docs -- --output docs/model_reference.md
  ```

  `bazel test //tools/docgen:model_docs_test` fails if the checked-in file is out of date.
