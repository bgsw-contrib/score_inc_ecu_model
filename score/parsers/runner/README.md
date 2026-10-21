# Parser Runner

The integration runner consumes registry pickle outputs from independently
built parser targets, merges their model elements, and
writes one aggregate pickle. An optional text output provides a JSON view of
the merged model.

`load_and_merge` in `parsers.bzl` accepts any number of target labels or pickle
file labels in a single `parsers` list. Each target must provide exactly one
default output file produced by `ModelRegistry.serialize()`. The runner does
not configure or invoke individual parsers; their own rules handle that.

```starlark
load_and_merge(
	name = "merged_model",
	parsers = [":parser_a", ":parser_b", ":parser_c"],
	out = "merged_model.pkl",
)
```

Inputs must be trusted pickle files containing ECU model objects. Their model
classes must be importable in the runner's Python environment; the standard
ECU model libraries are included, without dependencies on parser implementations.
Duplicate model element UUIDs are rejected. An empty list produces an empty registry.

Run the integration demo:

```sh
bazel run //score/parsers/runner/test/int/runner:load_and_merge_demo
```

Build the equivalent Bazel action and its artifacts:

```sh
bazel build //score/parsers/runner/test/int/runner:load_and_merge_build_demo
```

The aggregate pickle is also produced by `ModelRegistry.serialize()` and can
be loaded with `ModelRegistry.deserialize()` or used as an input to another
merge. The optional JSON output contains a `data_types` mapping keyed by model UUID.