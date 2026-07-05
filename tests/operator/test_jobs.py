"""Job-based reconcile tests: Persona B's run-to-completion mechanic.

These close the acceptance gap that the Deployment tests left open. A Job that
completes must drive the plan to Ready; a Job that fails past its backoff limit
must drive it to Failed and raise the NeedsAttention escalation the spec-02
agent will poll. Each test runs in its own namespace.
"""

import pytest
from kopf.testing import KopfRunner
from kubernetes import client

from tests.operator.conftest import load_fixture, runner_args, wait_until
from workload_operator.constants import GROUP, PLURAL, VERSION

pytestmark = pytest.mark.integration


def _create(ns: str, fixture: str) -> str:
    body = load_fixture(fixture)
    client.CustomObjectsApi().create_namespaced_custom_object(
        group=GROUP, version=VERSION, namespace=ns, plural=PLURAL, body=body
    )
    return body["metadata"]["name"]


def _status(ns: str, name: str) -> dict:
    plan = client.CustomObjectsApi().get_namespaced_custom_object(
        group=GROUP, version=VERSION, namespace=ns, plural=PLURAL, name=name
    )
    return plan.get("status", {})


def test_completed_job_makes_plan_ready(namespace: str) -> None:
    with KopfRunner(runner_args(namespace)) as runner:
        name = _create(namespace, "wp-job-complete.yaml")
        wait_until(lambda: _status(namespace, name).get("phase") == "Ready", timeout=120)
        assert _status(namespace, name)["readyCount"] == 1
    assert runner.exit_code == 0


def test_failed_job_makes_plan_failed_and_escalates(namespace: str) -> None:
    with KopfRunner(runner_args(namespace)) as runner:
        name = _create(namespace, "wp-job-fail.yaml")
        wait_until(lambda: _status(namespace, name).get("phase") == "Failed", timeout=120)
        conditions = _status(namespace, name).get("conditions", [])
        assert any(c["type"] == "NeedsAttention" for c in conditions)
    assert runner.exit_code == 0
