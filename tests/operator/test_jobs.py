"""Job-based reconcile tests: Persona B's run-to-completion mechanic.

These close the acceptance gap that the Deployment tests left open. A Job that
completes must drive the plan to Ready; a Job that fails past its backoff limit
must drive it to Failed and raise the NeedsAttention escalation the spec-02
agent will poll. Each test runs in its own namespace.
"""

import pytest
from kopf.testing import KopfRunner

from tests.operator.conftest import create_plan, get_plan, load_fixture, runner_args, wait_until

pytestmark = pytest.mark.integration


def _status(name: str) -> dict:
    return get_plan(name).get("status", {})


def test_completed_job_makes_plan_ready(namespace: str) -> None:
    with KopfRunner(runner_args(namespace)) as runner:
        name = create_plan(load_fixture("wp-job-complete.yaml"), namespace)
        wait_until(lambda: _status(name).get("phase") == "Ready", timeout=120)
        assert _status(name)["readyCount"] == 1
    assert runner.exit_code == 0


def test_failed_job_makes_plan_failed_and_escalates(namespace: str) -> None:
    with KopfRunner(runner_args(namespace)) as runner:
        name = create_plan(load_fixture("wp-job-fail.yaml"), namespace)
        wait_until(lambda: _status(name).get("phase") == "Failed", timeout=120)
        conditions = _status(name).get("conditions", [])
        assert any(c["type"] == "NeedsAttention" for c in conditions)
    assert runner.exit_code == 0
