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

from score.ecu_model.communication.binding import (
    CommunicationBinding,
    NetworkKind,
    ProtocolKind,
)
from score.ecu_model.model import ModelRegistry


class TestProtocolKind(unittest.TestCase):
    def test_protocol_kind_values(self) -> None:
        self.assertEqual(ProtocolKind.ARA_COM.value, "ARA::COM")
        self.assertEqual(ProtocolKind.ARA_DIAG.value, "ARA::DIAG")
        self.assertEqual(ProtocolKind.MW_COM.value, "MW::COM")
        self.assertEqual(ProtocolKind.MW_DIAG.value, "MW::DIAG")

    def test_network_kind_values(self) -> None:
        self.assertEqual(NetworkKind.SOMEIP.value, "SOMEIP")
        self.assertEqual(NetworkKind.IPC.value, "IPC")


class TestCommunicationBinding(unittest.TestCase):
    def setUp(self) -> None:
        ModelRegistry.elements.clear()

    def test_binding_preserves_protocol_and_network(self) -> None:
        binding = CommunicationBinding(
            protocol=ProtocolKind.ARA_COM,
            network=NetworkKind.SOMEIP,
            description="Service binding on SOME/IP",
        )

        self.assertEqual(binding.protocol, ProtocolKind.ARA_COM)
        self.assertEqual(binding.network, NetworkKind.SOMEIP)
        self.assertEqual(binding.description, "Service binding on SOME/IP")

    def test_binding_is_registered_in_model_registry(self) -> None:
        binding = CommunicationBinding(protocol=ProtocolKind.MW_COM, network=NetworkKind.IPC)

        self.assertIs(ModelRegistry.elements[binding.id], binding)

    def test_binding_accepts_enum_string_values(self) -> None:
        binding = CommunicationBinding(protocol="MW::DIAG", network="IPC")

        self.assertEqual(binding.protocol, ProtocolKind.MW_DIAG)
        self.assertEqual(binding.network, NetworkKind.IPC)

    def test_protocol_is_mandatory(self) -> None:
        with self.assertRaises(ValidationError):
            CommunicationBinding(network=NetworkKind.SOMEIP)

    def test_network_is_mandatory(self) -> None:
        with self.assertRaises(ValidationError):
            CommunicationBinding(protocol=ProtocolKind.ARA_COM)

    def test_unknown_protocol_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            CommunicationBinding(protocol="CAN", network=NetworkKind.SOMEIP)

    def test_unknown_network_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            CommunicationBinding(protocol=ProtocolKind.ARA_COM, network="FLEXRAY")

    def test_assignment_is_validated(self) -> None:
        binding = CommunicationBinding(protocol=ProtocolKind.ARA_COM, network=NetworkKind.SOMEIP)

        binding.network = NetworkKind.IPC
        self.assertEqual(binding.network, NetworkKind.IPC)

        with self.assertRaises(ValidationError):
            binding.protocol = "LIN"


if __name__ == "__main__":
    unittest.main()
