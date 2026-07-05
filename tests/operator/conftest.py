"""Fixtures and helpers for the operator's integration tests.

The integration layer talks to a real cluster, so every fixture here guards on
the minikube context: on any other context (CI, a remote cluster) the tests skip
rather than mutate infra.

Isolation is per test: each test runs in its own freshly created namespace
(wp-test-<id>) that is deleted at teardown. Unique namespaces mean tests can
never see each other's objects, so there is no shared state to leak and no
ordering dependence. The developer's default namespace is never touched.
"""

import subprocess
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

from workload_operator.constants import GROUP, PLURAL, VERSION

FIXTURES = Path(__file__).parent / "fixtures"
CRD_PATH = Path(__file__).parents[2] / "workload_operator" / "crd.yaml"


def load_fixture(name: str) -> dict[str, Any]:
    """Load a fixture manifest from the fixtures directory."""
    return yaml.safe_load((FIXTURES / name).read_text())


def runner_args(namespace: str) -> list[str]:
    """Build the KopfRunner argv scoped to one namespace."""
    return ["run", "-m", "workload_operator.handlers", "--namespace", namespace, "--standalone"]


def wait_until(predicate: Callable[[], bool], timeout: float = 45.0, interval: float = 1.0) -> None:
    """Poll a predicate until it is true or the timeout elapses.

    The integration answer is eventual, so we never sleep a fixed time; we poll a
    condition and fail loudly if it never holds.

    Parameters
    ----------
    predicate : callable
        Returns True once the awaited state holds. ApiException is swallowed so a
        not-found-yet object simply keeps the loop going.
    timeout, interval : float
        Total seconds to wait and seconds between polls.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if predicate():
                return
        except ApiException:
            pass
        time.sleep(interval)
    raise AssertionError(f"condition not met within {timeout}s")


def _current_context() -> str:
    result = subprocess.run(
        ["kubectl", "config", "current-context"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


@pytest.fixture(scope="session")
def cluster() -> None:
    """Guard the whole integration layer on the minikube context."""
    context = _current_context()
    if context != "minikube":
        pytest.skip(f"integration tests require the minikube context, got {context!r}")
    config.load_kube_config()


@pytest.fixture(scope="session")
def crd_applied(cluster: None) -> None:
    """Apply the CRD once for the whole test session."""
    subprocess.run(["kubectl", "apply", "-f", str(CRD_PATH)], check=True, capture_output=True)


def _strip_plan_finalizers(namespace: str) -> None:
    custom = client.CustomObjectsApi()
    try:
        response = custom.list_namespaced_custom_object(
            group=GROUP, version=VERSION, namespace=namespace, plural=PLURAL
        )
    except ApiException:
        return
    for item in response.get("items", []):
        try:
            custom.patch_namespaced_custom_object(
                group=GROUP,
                version=VERSION,
                namespace=namespace,
                plural=PLURAL,
                name=item["metadata"]["name"],
                body={"metadata": {"finalizers": []}},
            )
        except ApiException:
            pass


@pytest.fixture
def namespace(crd_applied: None) -> Any:
    """Create a unique namespace for one test and delete it afterwards.

    Unique names give perfect isolation with no ordering dependence. Teardown
    strips any plan finalizers first so the namespace cannot wedge in Terminating
    once the in-test operator has stopped; deleting the namespace then removes
    every child in one shot, even if the test failed midway.
    """
    name = f"wp-test-{uuid.uuid4().hex[:8]}"
    core = client.CoreV1Api()
    core.create_namespace(body={"metadata": {"name": name}})
    wait_until(lambda: core.read_namespace(name).status.phase == "Active", timeout=15)
    yield name
    _strip_plan_finalizers(name)
    try:
        core.delete_namespace(name=name)
    except ApiException:
        pass
