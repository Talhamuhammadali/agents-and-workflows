"""Integration test for the declare_plan seam.

Proves the whole agent-to-operator path end to end: a Gate 1 PlanModel is
translated to a WorkloadPlan, the agent's own client (built from a workspace
kubeconfig, never the ambient context) applies it, and the spec-01 operator
reconciles it to a healthy child. Runs in its own namespace, guarded on
minikube, polling for eventual state rather than sleeping.
"""

import pytest
from kopf.testing import KopfRunner
from kubernetes import client
from kubernetes.client.exceptions import ApiException

from agentic_patterns.infra_agent.state import Environment
from agentic_patterns.infra_agent.tools.clients import apply_cr, dynamic_client_for, get_cr_status
from agentic_patterns.infra_agent.tools.models import Component, PlanModel, build_workload_plan
from tests.agent.conftest import minikube_kubeconfig
from tests.operator.conftest import runner_args, wait_until

pytestmark = pytest.mark.integration

PLAN_NAME = "agent-web"


def _deployment(namespace: str, name: str):
    try:
        return client.AppsV1Api().read_namespaced_deployment(name, namespace)
    except ApiException:
        return None


def _plan() -> PlanModel:
    manifest = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "web"},
        "spec": {
            "replicas": 1,
            "selector": {"matchLabels": {"app": "web"}},
            "template": {
                "metadata": {"labels": {"app": "web"}},
                "spec": {"containers": [{"name": "web", "image": "nginx:1.27-alpine"}]},
            },
        },
    }
    return PlanModel(intent="provision", components=[Component(name="web", manifest=manifest)])


def test_declare_plan_applies_cr_and_operator_reconciles(namespace: str, tmp_path) -> None:
    env = Environment(
        name="local",
        kind="kubernetes",
        kubeconfig=minikube_kubeconfig(),
        context="minikube",
        namespace=namespace,
    )
    agent_client = dynamic_client_for(env, tmp_path)
    cr = build_workload_plan(_plan(), name=PLAN_NAME)

    with KopfRunner(runner_args(namespace)) as runner:
        apply_cr(agent_client, cr, namespace)
        wait_until(lambda: _deployment(namespace, "web") is not None, timeout=60)
        wait_until(
            lambda: (get_cr_status(agent_client, PLAN_NAME, namespace) or {}).get("phase") == "Ready",
            timeout=120,
        )
        assert (get_cr_status(agent_client, PLAN_NAME, namespace) or {}).get("readyCount") == 1
    assert runner.exit_code == 0
