"""Thin Kubernetes I/O layer for the operator.

Every cluster call lives behind a small function here so the Kopf handlers stay
thin and the decision logic in core stays pure and cluster-free. Server-side
apply is what keeps reconciliation idempotent: re-applying an unchanged child is
a no-op, so create, update, resume, and self-heal can all share one code path.
"""

from functools import lru_cache
from typing import Any

from kubernetes import config
from kubernetes.client import ApiClient
from kubernetes.dynamic import DynamicClient
from kubernetes.dynamic.exceptions import NotFoundError

FIELD_MANAGER = "workload-operator"


@lru_cache(maxsize=1)
def dynamic_client() -> DynamicClient:
    """Build the dynamic client once, preferring in-cluster config then kubeconfig.

    Cached so every handler and timer tick reuses one client instead of
    reloading kubeconfig and opening a new connection each call.

    Returns
    -------
    DynamicClient
        A client able to resolve and act on arbitrary resource kinds.
    """
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    return DynamicClient(ApiClient())


def apply_manifest(client: DynamicClient, manifest: dict[str, Any]) -> None:
    """Server-side apply one manifest, creating or updating it idempotently.

    Parameters
    ----------
    client : DynamicClient
        The client to apply through.
    manifest : dict
        A complete Kubernetes object, including namespace in its metadata.
    """
    resource = client.resources.get(api_version=manifest["apiVersion"], kind=manifest["kind"])
    metadata = manifest.get("metadata", {})
    client.server_side_apply(
        resource,
        body=manifest,
        name=metadata.get("name"),
        namespace=metadata.get("namespace"),
        field_manager=FIELD_MANAGER,
        force_conflicts=True,
    )


def get_object(client: DynamicClient, api_version: str, kind: str, name: str, namespace: str) -> dict[str, Any] | None:
    """Fetch one object as a plain dict, or None if it does not exist.

    Parameters
    ----------
    client : DynamicClient
        The client to read through.
    api_version, kind, name, namespace : str
        Coordinates of the object to fetch.

    Returns
    -------
    dict or None
        The live object as a dict, or None when it is absent.
    """
    resource = client.resources.get(api_version=api_version, kind=kind)
    try:
        obj = resource.get(name=name, namespace=namespace)
    except NotFoundError:
        return None
    return obj.to_dict()


def list_pods(client: DynamicClient, namespace: str, selector: dict[str, str]) -> list[dict[str, Any]]:
    """List the pods in a namespace matching a label selector, as plain dicts.

    Parameters
    ----------
    client : DynamicClient
        The client to read through.
    namespace : str
        Namespace to list pods in.
    selector : dict
        The matchLabels a workload controller owns its pods by. An empty
        selector returns nothing, so a controller with no selector never sweeps
        in unrelated pods.

    Returns
    -------
    list of dict
        The matching pods.
    """
    if not selector:
        return []
    label_selector = ",".join(f"{key}={value}" for key, value in selector.items())
    resource = client.resources.get(api_version="v1", kind="Pod")
    listing = resource.get(namespace=namespace, label_selector=label_selector)
    return [item.to_dict() for item in listing.items]


def delete_object(client: DynamicClient, api_version: str, kind: str, name: str, namespace: str) -> None:
    """Delete one object, ignoring the case where it is already gone.

    Parameters
    ----------
    client : DynamicClient
        The client to delete through.
    api_version, kind, name, namespace : str
        Coordinates of the object to delete.
    """
    resource = client.resources.get(api_version=api_version, kind=kind)
    try:
        resource.delete(name=name, namespace=namespace)
    except NotFoundError:
        pass
