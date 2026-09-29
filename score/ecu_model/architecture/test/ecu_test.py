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
from score.ecu_model.architecture.ecu import Ecu
from score.ecu_model.data_types.identifier import QualifiedName
from score.ecu_model.model import ModelRegistry


class TestEcu(unittest.TestCase):
    def setUp(self) -> None:
        ModelRegistry.elements.clear()

    def _application(self, name: str = "DrivingApp") -> Application:
        return Application(name=name, activities=[Activity(name="SpeedLimiter")])

    def test_ecu_groups_applications(self) -> None:
        application = self._application()
        ecu = Ecu(
            name="AdpEcu",
            namespace=QualifiedName(("adp", "platform")),
            description="Automated driving platform ECU",
            applications=[application],
            deployment_properties={"variant": "high"},
        )

        self.assertEqual(ecu.name.as_str, "AdpEcu")
        self.assertEqual(ecu.fully_qualified_name, "adp.platform.AdpEcu")
        self.assertIs(ecu.applications[0], application)
        self.assertEqual(ecu.deployment_properties, {"variant": "high"})

    def test_ecu_defaults(self) -> None:
        ecu = Ecu(name="AdpEcu", applications=[self._application()])

        self.assertEqual(ecu.fully_qualified_name, "AdpEcu")
        self.assertEqual(ecu.deployment_properties, {})

    def test_ecu_requires_at_least_one_application(self) -> None:
        with self.assertRaises(ValidationError):
            Ecu(name="AdpEcu", applications=[])

    def test_ecu_rejects_duplicate_application_names(self) -> None:
        with self.assertRaises(ValidationError):
            Ecu(name="AdpEcu", applications=[self._application(), self._application()])

    def test_ecu_accepts_applications_with_equal_names_in_different_namespaces(self) -> None:
        driving = Application(
            name="DrivingApp",
            namespace=QualifiedName(("adp", "driving")),
            activities=[Activity(name="SpeedLimiter")],
        )
        parking = Application(
            name="DrivingApp",
            namespace=QualifiedName(("adp", "parking")),
            activities=[Activity(name="SlotFinder")],
        )

        ecu = Ecu(name="AdpEcu", applications=[driving, parking])

        self.assertEqual(len(ecu.applications), 2)

    def test_ecu_rejects_blank_deployment_property_names(self) -> None:
        with self.assertRaises(ValidationError):
            Ecu(name="AdpEcu", applications=[self._application()], deployment_properties={"  ": "value"})


if __name__ == "__main__":
    unittest.main()
