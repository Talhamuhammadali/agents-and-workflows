"""Fixtures and helpers for the operator's integration tests.

The integration layer talks to a real cluster, so every fixture here guards on
the minikube context: on any other context (CI, a remote cluster) the tests skip
rather than mutate infra.

Isolation is per test: each test runs in its own freshly created namespace
(wp-test-<id>) that is deleted at teardown. Unique namespaces mean tests can
never see each other's objects, so there is no shared state to leak and no
ordering dependence. The developer's default namespace is never touched.
"""

import copy
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


def runner_args(namespace: str | None = None) -> list[str]:
    """Build the KopfRunner argv for the cluster-wide operator.

    The WorkloadPlan is cluster-scoped, so the operator watches the whole
    cluster; the namespace argument is accepted for call-site compatibility but
    no longer scopes the watch. Per-test isolation comes from unique plan names
    and per-test child namespaces instead.
    """
    return ["run", "-m", "workload_operator.handlers", "--all-namespaces", "--standalone"]


def create_plan(body: dict[str, Any], namespace: str) -> str:
    """Create a cluster-scoped plan whose children are pinned to one test namespace.

    Gives the plan a namespace-unique name and stamps that namespace onto every
    component manifest, so a cluster-scoped object still isolates per test: its
    children land in the test's own namespace and its name cannot collide.

    Returns
    -------
    str
        The unique name the plan was created under.
    """
    body = copy.deepcopy(body)
    name = f"{body['metadata']['name']}-{namespace}"
    body["metadata"]["name"] = name
    for component in body.get("spec", {}).get("components", []):
        component.setdefault("manifest", {}).setdefault("metadata", {})["namespace"] = namespace
    client.CustomObjectsApi().create_cluster_custom_object(group=GROUP, version=VERSION, plural=PLURAL, body=body)
    return name


def get_plan(name: str) -> dict[str, Any]:
    """Read a cluster-scoped plan by name."""
    return client.CustomObjectsApi().get_cluster_custom_object(group=GROUP, version=VERSION, plural=PLURAL, name=name)


def delete_plan(name: str) -> None:
    """Delete a cluster-scoped plan by name."""
    client.CustomObjectsApi().delete_cluster_custom_object(group=GROUP, version=VERSION, plural=PLURAL, name=name)


def patch_plan_components(name: str, components: list[dict[str, Any]], namespace: str) -> None:
    """Replace a cluster-scoped plan's components, keeping them pinned to the test namespace."""
    components = copy.deepcopy(components)
    for component in components:
        component.setdefault("manifest", {}).setdefault("metadata", {})["namespace"] = namespace
    client.CustomObjectsApi().patch_cluster_custom_object(
        group=GROUP, version=VERSION, plural=PLURAL, name=name, body={"spec": {"components": components}}
    )


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


def _cleanup_plans(namespace: str) -> None:
    """Delete every cluster-scoped plan this test created, stripping finalizers first.

    Plans are cluster-scoped, so they are not swept away by deleting the test
    namespace; they are matched by the per-test name suffix and removed here.
    Finalizers are stripped first so a plan cannot wedge once the in-test
    operator has stopped.
    """
    custom = client.CustomObjectsApi()
    try:
        response = custom.list_cluster_custom_object(group=GROUP, version=VERSION, plural=PLURAL)
    except ApiException:
        return
    for item in response.get("items", []):
        name = item["metadata"]["name"]
        if not name.endswith(f"-{namespace}"):
            continue
        try:
            custom.patch_cluster_custom_object(
                group=GROUP, version=VERSION, plural=PLURAL, name=name, body={"metadata": {"finalizers": []}}
            )
        except ApiException:
            pass
        try:
            custom.delete_cluster_custom_object(group=GROUP, version=VERSION, plural=PLURAL, name=name)
        except ApiException:
            pass


@pytest.fixture
def namespace(crd_applied: None) -> Any:
    """Create a unique namespace for one test and delete it afterwards.

    Unique names give perfect isolation with no ordering dependence. Teardown
    removes this test's cluster-scoped plans (matched by name suffix) first so
    nothing keeps reconciling, then deletes the namespace, which removes every
    child in one shot even if the test failed midway.
    """
    name = f"wp-test-{uuid.uuid4().hex[:8]}"
    core = client.CoreV1Api()
    core.create_namespace(body={"metadata": {"name": name}})
    wait_until(lambda: core.read_namespace(name).status.phase == "Active", timeout=15)
    yield name
    _cleanup_plans(name)
    try:
        core.delete_namespace(name=name)
    except ApiException:
        pass
