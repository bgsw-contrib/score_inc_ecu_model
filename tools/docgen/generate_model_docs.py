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

"""Generate GitHub flavoured Markdown reference documentation for the ECU model.

The generator imports the model packages, introspects every public class and
renders their docstrings, pydantic fields, enum members, properties and methods
into a single Markdown file. Documentation therefore never drifts from the code:
the docstrings in the sources are the single point of truth.
"""

from __future__ import annotations

import argparse
import enum
import importlib
import inspect
import os
import pkgutil
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

DEFAULT_PACKAGES = ("score.ecu_model",)

# Markdown flavour of //third_party/cr_checker:templates. The year is fixed so the output stays reproducible.
COPYRIGHT_HEADER = """<!----
*******************************************************************************
Copyright (c) 2026 Contributors to the Eclipse Foundation

See the NOTICE file(s) distributed with this work for additional
information regarding copyright ownership.

This program and the accompanying materials are made available under the
terms of the Apache License Version 2.0 which is available at
https://www.apache.org/licenses/LICENSE-2.0

SPDX-License-Identifier: Apache-2.0
*******************************************************************************
-->"""

# Google style docstring sections rendered as bullet lists instead of paragraphs.
DOCSTRING_SECTIONS = (
    "Args:",
    "Arguments:",
    "Attributes:",
    "Raises:",
    "Returns:",
    "Yields:",
    "Note:",
    "Notes:",
    "Example:",
    "Examples:",
)

# Dotted prefixes made of lowercase segments are module paths; CamelCase owners like `DataTypeKind.ARRAY` are kept.
_MODULE_PREFIX_PATTERN = re.compile(r"(?:\b[a-z_][a-z0-9_]*\.)+(?=[A-Za-z_])")
_IDENTIFIER_PATTERN = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
# Enum reprs such as `<DataTypeKind.ARRAY: 'array'>` show up inside Literal[...] annotations.
_ENUM_REPR_PATTERN = re.compile(r"<([A-Za-z_][A-Za-z0-9_.]*): [^>]*>")


def _iter_modules(package_names: list[str]) -> list[ModuleType]:
    """Import all non-test modules of the given packages, recursively."""
    modules: dict[str, ModuleType] = {}
    for package_name in package_names:
        package = importlib.import_module(package_name)
        modules[package_name] = package
        for info in pkgutil.walk_packages(package.__path__, prefix=f"{package_name}."):
            if any(part in ("test", "tests") for part in info.name.split(".")):
                continue
            modules[info.name] = importlib.import_module(info.name)
    return [modules[name] for name in sorted(modules)]


def _public_classes(module: ModuleType) -> list[type]:
    """Return the public classes defined in this module, in source order."""
    classes = [
        obj
        for name, obj in vars(module).items()
        if not name.startswith("_") and inspect.isclass(obj) and obj.__module__ == module.__name__
    ]
    return sorted(classes, key=lambda cls: inspect.getsourcelines(cls)[1])


def _format_annotation(annotation: Any) -> str:
    """Render a type annotation without module qualifiers."""
    if annotation is inspect.Signature.empty or annotation is None:
        return ""
    if isinstance(annotation, str):
        text = annotation
    elif inspect.isclass(annotation):
        text = annotation.__name__
    else:
        # Generic aliases (dict[str, object], Literal[...], ...) only render their parameters via str().
        text = _ENUM_REPR_PATTERN.sub(r"\1", str(annotation))
    return _MODULE_PREFIX_PATTERN.sub("", text)


def _escape_cell(text: str) -> str:
    """Escape a value so it can be placed inside a Markdown table cell."""
    return text.replace("|", "\\|").replace("\n", " ")


def _linkify(text: str, anchors: dict[str, str], in_table: bool = False) -> str:
    """Render a type expression, turning every documented type name into a link to its section."""

    def literal(chunk: str) -> str:
        return _escape_cell(chunk) if in_table else chunk

    matches = [match for match in _IDENTIFIER_PATTERN.finditer(text) if match.group() in anchors]
    if not matches:
        # Nothing to link, so the whole expression can stay a single code span.
        return f"`{literal(text)}`"
    parts: list[str] = []
    position = 0
    for match in matches:
        parts.append(literal(text[position : match.start()]))
        parts.append(f"[`{match.group()}`](#{anchors[match.group()]})")
        position = match.end()
    parts.append(literal(text[position:]))
    return "".join(parts)


def _format_docstring(owner: Any) -> str:
    """Render the docstring of a class or member as Markdown."""
    doc = owner.__doc__
    if not doc or not doc.strip():
        return ""
    rendered: list[str] = []
    in_section = False
    for line in inspect.cleandoc(doc).splitlines():
        stripped = line.strip()
        if stripped in DOCSTRING_SECTIONS:
            rendered.extend(["", f"**{stripped}**", ""])
            in_section = True
        elif not stripped:
            in_section = False
            rendered.append("")
        elif in_section:
            rendered.append(f"- {stripped}")
        else:
            rendered.append(stripped)
    return "\n".join(rendered).strip()


def _has_own_docstring(member: Any) -> bool:
    """Tell whether the member documents itself instead of inheriting a docstring."""
    doc = getattr(member, "__doc__", None)
    if not doc:
        return False
    unwrapped = getattr(member, "__func__", member)
    parent = getattr(unwrapped, "__objclass__", None)
    return doc != getattr(parent, "__doc__", None)


def _documented_members(cls: type) -> list[tuple[str, str, Any]]:
    """Return (name, kind, member) triples for the documentable members of a class."""
    members: list[tuple[str, str, Any]] = []
    for name, member in vars(cls).items():
        if name.startswith("_") and not (name.endswith("__") and _has_own_docstring(member)):
            continue
        if isinstance(member, property):
            members.append((name, "property", member))
        elif isinstance(member, classmethod):
            members.append((name, "classmethod", member.__func__))
        elif isinstance(member, staticmethod):
            members.append((name, "staticmethod", member.__func__))
        elif inspect.isfunction(member):
            members.append((name, "method", member))
    return members


def _render_enum(cls: type[enum.Enum]) -> list[str]:
    lines = ["| Member | Value |", "| --- | --- |"]
    lines += [f"| `{member.name}` | `{member.value!r}` |" for member in cls]
    return ["**Members**", "", *lines, ""]


def _render_fields(cls: type, anchors: dict[str, str]) -> list[str]:
    """Render the pydantic model fields declared by this class as a table."""
    fields = getattr(cls, "model_fields", None)
    if not isinstance(fields, dict):
        return []
    own_annotations = getattr(cls, "__annotations__", {})
    rows = []
    for name, field in fields.items():
        if name not in own_annotations:
            continue
        if field.is_required():
            default = "_required_"
        elif field.default_factory is not None:
            # Only the name, the repr of a plain function contains its memory address.
            factory = getattr(field.default_factory, "__name__", type(field.default_factory).__name__)
            default = f"`{factory}()`"
        else:
            value = field.default
            default = f"`{type(value).__name__}.{value.name}`" if isinstance(value, enum.Enum) else f"`{value!r}`"
        annotation = _linkify(_format_annotation(field.annotation), anchors, in_table=True)
        rows.append(f"| `{name}` | {annotation} | {default} | {_escape_cell(field.description or '')} |")
    if not rows:
        return []
    return ["**Fields**", "", "| Field | Type | Default | Description |", "| --- | --- | --- | --- |", *rows, ""]


def _validator_summary(doc: str | None, default: str) -> str:
    """Use the first docstring sentence of a validator, or a generic fallback."""
    if not doc or not doc.strip():
        return default
    return inspect.cleandoc(doc).split("\n\n")[0].replace("\n", " ")


def _render_validators(cls: type) -> list[str]:
    """Render the pydantic validators declared by this class as a table."""
    decorators = getattr(cls, "__pydantic_decorators__", None)
    if decorators is None:
        return []
    rows = []
    for name, decorator in getattr(decorators, "field_validators", {}).items():
        # Inherited validators are documented on the class that declares them.
        if name not in vars(cls):
            continue
        fields = ", ".join(f"`{field}`" for field in decorator.info.fields) or "_all fields_"
        doc = _validator_summary(decorator.func.__doc__, f"Validates {fields}.")
        rows.append(f"| `{name}` | field, {decorator.info.mode} | {fields} | {_escape_cell(doc)} |")
    for name, decorator in getattr(decorators, "model_validators", {}).items():
        if name not in vars(cls):
            continue
        doc = _validator_summary(decorator.func.__doc__, "Validates the model as a whole.")
        rows.append(f"| `{name}` | model, {decorator.info.mode} | _the whole model_ | {_escape_cell(doc)} |")
    if not rows:
        return []
    return [
        "**Validators**",
        "",
        "| Validator | Kind | Applies to | Description |",
        "| --- | --- | --- | --- |",
        *rows,
        "",
    ]


def _diagram_relations(documented: list[tuple[ModuleType, list[type]]]) -> list[str]:
    """Collect Mermaid class diagram relations: inheritance plus references between documented classes."""
    classes = [cls for _, module_classes in documented for cls in module_classes]
    names = {cls.__name__ for cls in classes}
    relations: list[str] = []
    involved: set[str] = set()
    references: dict[tuple[str, str], list[str]] = {}
    for cls in classes:
        for base in cls.__bases__:
            if base.__name__ in names:
                relations.append(f"    {base.__name__} <|-- {cls.__name__}")
                involved |= {base.__name__, cls.__name__}
        fields = getattr(cls, "model_fields", None)
        if not isinstance(fields, dict):
            continue
        for field_name, field in fields.items():
            if field_name not in getattr(cls, "__annotations__", {}):
                continue
            annotation = _format_annotation(field.annotation)
            if annotation.startswith("Literal"):
                # Discriminator fields repeat the enum for every subclass without adding information.
                continue
            targets = {token for token in _IDENTIFIER_PATTERN.findall(annotation) if token in names}
            for target in sorted(targets - {cls.__name__}):
                labels = references.setdefault((cls.__name__, target), [])
                if field_name not in labels:
                    labels.append(field_name)
                involved |= {cls.__name__, target}
    relations += [f"    {source} --> {target} : {', '.join(labels)}" for (source, target), labels in references.items()]
    isolated = [f"    class {name}" for name in sorted(names - involved)]
    return isolated + relations


def _render_diagram(documented: list[tuple[ModuleType, list[type]]]) -> list[str]:
    """Render an overview class diagram of the documented model."""
    return [
        "## Overview",
        "",
        "Inheritance (`<|--`) and references between the documented types; members are omitted on purpose.",
        "",
        "```mermaid",
        "classDiagram",
        *_diagram_relations(documented),
        "```",
        "",
    ]


def _render_member(name: str, kind: str, member: Any) -> list[str]:
    if kind == "property":
        signature = ""
        documented = member.fget
    else:
        signature = _MODULE_PREFIX_PATTERN.sub("", str(inspect.signature(member)))
        documented = member
    lines = [f"#### `{name}{signature}`", "", f"_{kind}_", ""]
    doc = _format_docstring(documented)
    if doc:
        lines += [doc, ""]
    return lines


def _render_class(cls: type, anchors: dict[str, str]) -> list[str]:
    bases = ", ".join(_linkify(base.__name__, anchors) for base in cls.__bases__ if base is not object)
    lines = [f"### `{cls.__name__}`", ""]
    if bases:
        lines += [f"Inherits from {bases}.", ""]
    doc = _format_docstring(cls)
    if doc:
        lines += [doc, ""]
    if issubclass(cls, enum.Enum):
        lines += _render_enum(cls)
    lines += _render_fields(cls, anchors)
    lines += _render_validators(cls)
    for name, kind, member in _documented_members(cls):
        lines += _render_member(name, kind, member)
    return lines


def _anchor(text: str) -> str:
    """Build the GitHub heading anchor for the given heading text."""
    return re.sub(r"[^a-z0-9 -]", "", text.lower()).replace(" ", "-")


def render(modules: list[ModuleType], title: str) -> str:
    """Render the Markdown documentation for all given modules."""
    documented = [(module, _public_classes(module)) for module in modules]
    documented = [(module, classes) for module, classes in documented if classes]

    # A type is only linkable once it has a heading, and ambiguous names would link to the wrong one.
    names = [cls.__name__ for _, classes in documented for cls in classes]
    anchors = {name: _anchor(name) for name in names if names.count(name) == 1}

    body: list[str] = _render_diagram(documented)
    for module, classes in documented:
        body += [f"## `{module.__name__}`", ""]
        module_doc = _format_docstring(module)
        if module_doc:
            body += [module_doc, ""]
        for cls in classes:
            body += _render_class(cls, anchors)

    header = [
        COPYRIGHT_HEADER,
        "",
        f"# {title}",
        "",
        "<!-- Generated by tools/docgen:generate_model_docs. Do not edit manually,",
        "     update the docstrings in the sources and regenerate instead. -->",
        "",
    ]
    return "\n".join([*header, *body]).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="Markdown file to write, relative to the workspace root")
    parser.add_argument(
        "--package",
        action="append",
        dest="packages",
        default=None,
        help=f"Python package to document, repeatable (default: {', '.join(DEFAULT_PACKAGES)})",
    )
    parser.add_argument("--title", default="ECU Model Reference", help="Title of the generated document")
    parser.add_argument("--check", action="store_true", help="Fail if the output file is not up to date")
    args = parser.parse_args(argv)

    content = render(_iter_modules(args.packages or list(DEFAULT_PACKAGES)), args.title)

    # `bazel run` executes in the runfiles tree, so resolve relative outputs against the source tree.
    workspace = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
    output = Path(args.output)
    if workspace and not output.is_absolute():
        output = Path(workspace) / output

    if args.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != content:
            print(
                f"{output} is out of date, run: bazel run //tools/docgen:generate_model_docs -- --output docs/model_reference.md",
                file=sys.stderr,
            )
            return 1
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
