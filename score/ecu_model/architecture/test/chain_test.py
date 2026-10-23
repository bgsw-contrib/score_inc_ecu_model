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
from datetime import timedelta

from pydantic import ValidationError

from score.ecu_model.architecture.activity import Activity
from score.ecu_model.architecture.application import Application
from score.ecu_model.architecture.chain import Chain, ChainNode
from score.ecu_model.data_types.identifier import QualifiedName
from score.ecu_model.model import ModelRegistry


class TestChain(unittest.TestCase):
    def setUp(self) -> None:
        ModelRegistry.elements.clear()
        self.sensor = Activity(name="Sensor")
        self.fusion = Activity(name="Fusion")
        self.sensing = Application(name="SensingApp", activities=[self.sensor])
        self.perception = Application(name="PerceptionApp", activities=[self.fusion])

    def _chain(self, **overrides: object) -> Chain:
        arguments: dict[str, object] = {
            "name": "Chain100ms",
            "cycle_time": timedelta(milliseconds=100),
            "applications": [self.sensing, self.perception],
            "nodes": [
                ChainNode(activity=self.sensor),
                ChainNode(activity=self.fusion, triggered_by=[self.sensor]),
            ],
        }
        arguments.update(overrides)
        return Chain(**arguments)  # type: ignore[arg-type]

    def test_chain_describes_the_trigger_graph_across_applications(self) -> None:
        chain = self._chain(namespace=QualifiedName(("adp", "scheduling")))

        self.assertEqual(chain.fully_qualified_name, "adp.scheduling.Chain100ms")
        self.assertEqual(chain.cycle_time, timedelta(milliseconds=100))
        self.assertIs(chain.nodes[1].triggered_by[0], self.sensor)

    def test_chain_rejects_non_positive_cycle_time(self) -> None:
        with self.assertRaises(ValidationError):
            self._chain(cycle_time=timedelta(0))

    def test_chain_rejects_an_activity_scheduled_twice(self) -> None:
        with self.assertRaises(ValidationError) as context:
            self._chain(
                nodes=[
                    ChainNode(activity=self.sensor),
                    ChainNode(activity=self.sensor),
                ]
            )
        self.assertIn("scheduled more than once", str(context.exception))

    def test_chain_rejects_an_activity_outside_its_applications(self) -> None:
        foreign = Activity(name="Planner")
        Application(name="PlanningApp", activities=[foreign])

        with self.assertRaises(ValidationError) as context:
            self._chain(
                nodes=[
                    ChainNode(activity=self.sensor),
                    ChainNode(activity=self.fusion, triggered_by=[self.sensor]),
                    ChainNode(activity=foreign, triggered_by=[self.fusion]),
                ]
            )
        self.assertIn("does not belong to any application of this chain", str(context.exception))

    def test_chain_rejects_an_application_without_scheduled_activity(self) -> None:
        with self.assertRaises(ValidationError) as context:
            self._chain(nodes=[ChainNode(activity=self.sensor)])
        self.assertIn("does not contribute any activity to this chain", str(context.exception))

    def test_chain_rejects_self_trigger(self) -> None:
        with self.assertRaises(ValidationError) as context:
            self._chain(
                nodes=[
                    ChainNode(activity=self.sensor),
                    ChainNode(activity=self.fusion, triggered_by=[self.fusion]),
                ]
            )
        self.assertIn("must not trigger itself", str(context.exception))

    def test_chain_rejects_a_predecessor_outside_the_chain(self) -> None:
        planner = Activity(name="Planner")

        with self.assertRaises(ValidationError) as context:
            self._chain(
                nodes=[
                    ChainNode(activity=self.sensor),
                    ChainNode(activity=self.fusion, triggered_by=[planner]),
                ]
            )
        self.assertIn("which is not part of this chain", str(context.exception))

    def test_chain_requires_a_root_activity(self) -> None:
        with self.assertRaises(ValidationError) as context:
            self._chain(
                nodes=[
                    ChainNode(activity=self.sensor, triggered_by=[self.fusion]),
                    ChainNode(activity=self.fusion, triggered_by=[self.sensor]),
                ]
            )
        self.assertIn("at least one root activity", str(context.exception))

    def test_chain_rejects_a_trigger_cycle(self) -> None:
        cleanup = Activity(name="Cleanup")
        self.perception = Application(name="PerceptionApp", activities=[self.fusion, cleanup])

        with self.assertRaises(ValidationError) as context:
            self._chain(
                nodes=[
                    ChainNode(activity=self.sensor),
                    ChainNode(activity=self.fusion, triggered_by=[cleanup]),
                    ChainNode(activity=cleanup, triggered_by=[self.fusion]),
                ]
            )
        self.assertIn("trigger cycle", str(context.exception))

    def test_chain_requires_at_least_one_node(self) -> None:
        with self.assertRaises(ValidationError):
            self._chain(nodes=[])


if __name__ == "__main__":
    unittest.main()
