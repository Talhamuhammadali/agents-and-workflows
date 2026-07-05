"""Reconcile-behavior tests: the operator's milestones as executable specs.

Each test runs in its own namespace with its own in-process operator
(KopfRunner), drives one milestone, and asserts eventual state by polling (never
a fixed sleep). Covers create, health, cascade cleanup, resume, self-heal, and
pruning.
"""

import pytest
from kopf.testing import KopfRunner
from kubernetes import client
from kubernetes.client.exceptions import ApiException

from tests.operator.conftest import load_fixture, runner_args, wait_until
from workload_operator.constants import GROUP, LABEL_COMPONENT, LABEL_PLAN, PLURAL, VERSION

pytestmark = pytest.mark.integration

PLAN = load_fixture("wp-good.yaml")
PLAN_NAME = PLAN["metadata"]["name"]


def _create_plan(ns: str) -> None:
    client.CustomObjectsApi().create_namespaced_custom_object(
        group=GROUP, version=VERSION, namespace=ns, plural=PLURAL, body=PLAN
    )


def _delete_plan(ns: str) -> None:
    client.CustomObjectsApi().delete_namespaced_custom_object(
        group=GROUP, version=VERSION, namespace=ns, plural=PLURAL, name=PLAN_NAME
    )


def _plan(ns: str) -> dict:
    return client.CustomObjectsApi().get_namespaced_custom_object(
        group=GROUP, version=VERSION, namespace=ns, plural=PLURAL, name=PLAN_NAME
    )


def _patch_components(ns: str, components: list) -> None:
    client.CustomObjectsApi().patch_namespaced_custom_object(
        group=GROUP, version=VERSION, namespace=ns, plural=PLURAL, name=PLAN_NAME, body={"spec": {"components": components}}
    )


def _deployment(ns: str, name: str):
    try:
        return client.AppsV1Api().read_namespaced_deployment(name, ns)
    except ApiException:
        return None


def _configmap(ns: str, name: str):
    try:
        return client.CoreV1Api().read_namespaced_config_map(name, ns)
    except ApiException:
        return None


def test_reconcile_creates_children_with_owner_refs_and_labels(namespace: str) -> None:
    with KopfRunner(runner_args(namespace)) as runner:
        _create_plan(namespace)
        wait_until(lambda: _deployment(namespace, "web") is not None)
        dep = _deployment(namespace, "web")
        ref = dep.metadata.owner_references[0]
        assert ref.kind == "WorkloadPlan"
        assert ref.name == PLAN_NAME
        assert ref.controller is True
        assert dep.metadata.labels[LABEL_PLAN] == PLAN_NAME
        assert dep.metadata.labels[LABEL_COMPONENT] == "web"
        cm = client.CoreV1Api().read_namespaced_config_map("web-config", namespace)
        assert cm.metadata.owner_references[0].name == PLAN_NAME
    assert runner.exit_code == 0


def test_health_sweep_flips_phase_to_ready(namespace: str) -> None:
    with KopfRunner(runner_args(namespace)) as runner:
        _create_plan(namespace)
        wait_until(lambda: _plan(namespace).get("status", {}).get("phase") == "Ready", timeout=60)
        assert _plan(namespace)["status"]["readyCount"] == 2
    assert runner.exit_code == 0


def test_cascade_delete_removes_children(namespace: str) -> None:
    with KopfRunner(runner_args(namespace)) as runner:
        _create_plan(namespace)
        wait_until(lambda: _deployment(namespace, "web") is not None)
        _delete_plan(namespace)
        wait_until(lambda: _deployment(namespace, "web") is None, timeout=60)
    assert runner.exit_code == 0


def test_resume_adopts_a_preexisting_plan(namespace: str) -> None:
    _create_plan(namespace)
    assert _deployment(namespace, "web") is None
    with KopfRunner(runner_args(namespace)) as runner:
        wait_until(lambda: _deployment(namespace, "web") is not None, timeout=60)
    assert runner.exit_code == 0


def test_reconcile_prunes_a_removed_component(namespace: str) -> None:
    with KopfRunner(runner_args(namespace)) as runner:
        _create_plan(namespace)
        wait_until(lambda: _deployment(namespace, "web") is not None and _configmap(namespace, "web-config") is not None)
        _patch_components(namespace, [PLAN["spec"]["components"][0]])
        wait_until(lambda: _configmap(namespace, "web-config") is None, timeout=60)
        assert _deployment(namespace, "web") is not None
    assert runner.exit_code == 0


def test_self_heal_recreates_a_deleted_child(namespace: str) -> None:
    with KopfRunner(runner_args(namespace)) as runner:
        _create_plan(namespace)
        wait_until(lambda: _deployment(namespace, "web") is not None)
        original_uid = _deployment(namespace, "web").metadata.uid
        client.AppsV1Api().delete_namespaced_deployment("web", namespace)
        wait_until(
            lambda: _deployment(namespace, "web") is not None
            and _deployment(namespace, "web").metadata.uid != original_uid,
            timeout=60,
        )
    assert runner.exit_code == 0
