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
from score.ecu_model.common.asil_level import AsilLevel
from score.ecu_model.common.version import Version
from score.ecu_model.communication.binding import CommunicationBinding, NetworkKind, ProtocolKind
from score.ecu_model.communication.message_channel import MessageChannel
from score.ecu_model.communication.message_port import ProvidedMessagePort, RequiredMessagePort
from score.ecu_model.communication.service_interface import InterfaceDefinition, ServiceInterface
from score.ecu_model.data_types.identifier import QualifiedName
from score.ecu_model.model import ModelRegistry


class TestActivity(unittest.TestCase):
    def setUp(self) -> None:
        ModelRegistry.elements.clear()

    def _input_port(self, name: str = "SpeedIn") -> RequiredMessagePort:
        return RequiredMessagePort(
            name=name,
            channel=MessageChannel(name="SpeedChannel", data_type="SpeedData"),
            binding=CommunicationBinding(protocol=ProtocolKind.MW_COM, network=NetworkKind.IPC),
        )

    def _output_port(self, name: str = "SpeedOut") -> ProvidedMessagePort:
        return ProvidedMessagePort(
            name=name,
            channel=MessageChannel(name="SpeedChannel", data_type="SpeedData"),
            binding=CommunicationBinding(protocol=ProtocolKind.ARA_COM, network=NetworkKind.SOMEIP),
        )

    def _service_interface(self) -> ServiceInterface:
        return ServiceInterface(
            name="VehicleStateDeployment",
            namespace="deployment",
            design_element=InterfaceDefinition(name="VehicleState", version=Version()),
            service_id=42,
        )

    def test_activity_preserves_scheduling_metadata_and_ports(self) -> None:
        input_port = self._input_port()
        output_port = self._output_port()
        activity = Activity(
            name="SpeedLimiter",
            namespace=QualifiedName(("adp", "driving")),
            asil=AsilLevel.B,
            description="Limits the requested speed",
            version=Version(major=2, minor=1, patch=0),
            inputs=[input_port],
            outputs=[output_port],
        )

        self.assertEqual(activity.name.as_str, "SpeedLimiter")
        self.assertEqual(activity.fully_qualified_name, "adp.driving.SpeedLimiter")
        self.assertEqual(activity.asil, AsilLevel.B)
        self.assertEqual(activity.version, Version(major=2, minor=1, patch=0))
        self.assertIs(activity.inputs[0], input_port)
        self.assertIs(activity.outputs[0], output_port)

    def test_activity_rejects_provided_port_as_input(self) -> None:
        with self.assertRaises(ValidationError):
            Activity(name="SpeedLimiter", inputs=[self._output_port()])

    def test_activity_defaults(self) -> None:
        activity = Activity(name="SpeedLimiter")

        self.assertEqual(activity.asil, AsilLevel.QM)
        self.assertEqual(activity.version, Version(major=1, minor=0, patch=0))
        self.assertEqual(activity.namespace.as_str, "")
        self.assertEqual(activity.inputs, [])
        self.assertEqual(activity.outputs, [])

    def test_activity_rejects_invalid_name(self) -> None:
        with self.assertRaises(ValidationError):
            Activity(name="1SpeedLimiter")


if __name__ == "__main__":
    unittest.main()
