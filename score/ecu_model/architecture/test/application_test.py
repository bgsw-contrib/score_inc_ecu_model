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

import unittest

from pydantic import ValidationError

from score.ecu_model.architecture.activity import Activity
from score.ecu_model.architecture.application import Application
from score.ecu_model.common.version import Version
from score.ecu_model.communication.binding import CommunicationBinding, NetworkKind, ProtocolKind
from score.ecu_model.communication.service_interface import InterfaceDefinition, ServiceInterface
from score.ecu_model.communication.service_port import ProvidedServicePort
from score.ecu_model.data_types.identifier import QualifiedName
from score.ecu_model.model import ModelRegistry


class TestApplication(unittest.TestCase):
    def setUp(self) -> None:
        ModelRegistry.elements.clear()

    def _activity(self, name: str = "SpeedLimiter") -> Activity:
        return Activity(name=name)

    def _service_port(self) -> ProvidedServicePort:
        return ProvidedServicePort(
            name="VehicleStateProvider",
            interface=ServiceInterface(
                name="VehicleStateDeployment",
                namespace="deployment",
                design_element=InterfaceDefinition(name="VehicleState", version=Version()),
                service_id=42,
            ),
            binding=CommunicationBinding(protocol=ProtocolKind.ARA_COM, network=NetworkKind.SOMEIP),
        )

    def test_application_groups_activities_and_service_ports(self) -> None:
        activity = self._activity()
        service_port = self._service_port()
        application = Application(
            name="DrivingApp",
            namespace=QualifiedName(("adp", "driving")),
            description="Longitudinal driving application",
            activities=[activity],
            provided_service_ports=[service_port],
            deployment_properties={"machine": "adp"},
        )

        self.assertEqual(application.name.as_str, "DrivingApp")
        self.assertEqual(application.fully_qualified_name, "adp.driving.DrivingApp")
        self.assertIs(application.activities[0], activity)
        self.assertIs(application.provided_service_ports[0], service_port)
        self.assertEqual(application.required_service_ports, [])
        self.assertEqual(application.deployment_properties, {"machine": "adp"})

    def test_application_requires_at_least_one_activity(self) -> None:
        with self.assertRaises(ValidationError):
            Application(name="DrivingApp", activities=[])

    def test_application_rejects_duplicate_activity_names(self) -> None:
        with self.assertRaises(ValidationError):
            Application(
                name="DrivingApp",
                activities=[self._activity(), self._activity()],
            )

    def test_application_rejects_blank_deployment_property_names(self) -> None:
        with self.assertRaises(ValidationError):
            Application(
                name="DrivingApp",
                activities=[self._activity()],
                deployment_properties={"  ": "value"},
            )


if __name__ == "__main__":
    unittest.main()
