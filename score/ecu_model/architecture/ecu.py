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

from __future__ import annotations

from pydantic import Field, field_validator, model_validator

from score.ecu_model.architecture.application import Application
from score.ecu_model.data_types.identifier import Identifier, QualifiedName
from score.ecu_model.model import ModelElement


class Ecu(ModelElement):
    """A deployment target grouping the applications that run on it."""

    name: Identifier = Field(description="Identifier of the ECU, unique within the owning system")
    namespace: QualifiedName = Field(
        default_factory=QualifiedName,
        description="Namespace in which the ECU is declared",
    )
    applications: list[Application] = Field(
        min_length=1,
        description="Applications deployed on this ECU",
    )
    deployment_properties: dict[str, object] = Field(
        default_factory=dict,
        description="Deployment metadata attached to this ECU",
    )

    @field_validator("deployment_properties")
    @classmethod
    def _validate_property_names(cls, value: dict[str, object]) -> dict[str, object]:
        if any(not key.strip() for key in value):
            raise ValueError("deployment property names must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_unique_application_names(self) -> Ecu:
        application_names = [application.fully_qualified_name for application in self.applications]
        if len(application_names) != len(set(application_names)):
            raise ValueError("application names must be unique within an ECU")
        return self

    @property
    def fully_qualified_name(self) -> str:
        """Return the dot-separated ECU name."""
        return QualifiedName((*self.namespace.names, self.name)).as_str
