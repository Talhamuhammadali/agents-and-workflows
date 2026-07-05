"""Crash-loop escalation test: a Deployment a Job's terminal state cannot express.

A Deployment never marks itself failed the way a Job past its backoff limit
does, so the operator reads the pods: a container stuck in CrashLoopBackOff must
drive the plan to Failed and raise the NeedsAttention escalation the spec-02
agent polls through check_escalations. Runs in its own namespace.
"""

import pytest
from kopf.testing import KopfRunner

from tests.operator.conftest import create_plan, get_plan, load_fixture, runner_args, wait_until

pytestmark = pytest.mark.integration


def _status(name: str) -> dict:
    return get_plan(name).get("status", {})


def test_crashlooping_deployment_makes_plan_failed_and_escalates(namespace: str) -> None:
    with KopfRunner(runner_args(namespace)) as runner:
        name = create_plan(load_fixture("wp-deploy-crash.yaml"), namespace)
        wait_until(lambda: _status(name).get("phase") == "Failed", timeout=180)
        conditions = _status(name).get("conditions", [])
        assert any(c["type"] == "NeedsAttention" for c in conditions)
    assert runner.exit_code == 0
