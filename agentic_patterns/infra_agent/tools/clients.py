"""Cluster client seam for the infrastructure agent.

The target client is always built from a kubeconfig written into the workspace
and loaded explicitly, so the agent can only ever reach the environment it was
handed and never the ambient default context.
"""

import os
import subprocess
from pathlib import Path

from kubernetes import config, dynamic
from kubernetes.client.exceptions import ApiException

from agentic_patterns.infra_agent.state import Environment
from workload_operator.constants import API_VERSION, KIND

FIELD_MANAGER = "infra-agent"
WORKSPACE_KUBECONFIG = ".kubeconfig"


def materialize_kubeconfig(env: Environment, workspace: Path) -> Path:
    """Write a kubernetes environment's kubeconfig blob into the workspace.

    Parameters
    ----------
    env
        A kubernetes environment carrying a self-contained kubeconfig blob.
    workspace
        Directory the kubeconfig is written into.

    Returns
    -------
    Path
        Path to the written kubeconfig file.
    """
    if env.kubeconfig is None:
        raise ValueError(f"environment {env.name} has no kubeconfig")
    path = Path(workspace) / f"kubeconfig-{env.name}"
    path.write_text(env.kubeconfig)
    return path


def _current_context(kubeconfig: Path) -> str | None:
    """Return a kubeconfig file's current-context, or None."""
    result = subprocess.run(
        ["kubectl", "config", "view", f"--kubeconfig={kubeconfig}", "--output", "jsonpath={.current-context}"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip() or None


def materialize_workspace_kubeconfig(environments: list[Environment], workspace: Path) -> Path | None:
    """Merge every kubernetes environment into one workspace kubeconfig for shell tools.

    Each environment's selected context is renamed to its environment name, so the
    single file exposes one predictable context per environment that the agent can
    select with kubectl. Only the given environments are reachable through it.

    Parameters
    ----------
    environments
        The run's environments; non-kubernetes ones are ignored.
    workspace
        Directory the merged kubeconfig is written into.

    Returns
    -------
    Path or None
        Path to the merged kubeconfig, or None when no kubernetes environment exists.
    """
    kube_envs = [env for env in environments if env.kind == "kubernetes" and env.kubeconfig]
    if not kube_envs:
        return None

    sources: list[str] = []
    for env in kube_envs:
        blob = env.kubeconfig
        if blob is None:
            continue
        source = Path(workspace) / f"{WORKSPACE_KUBECONFIG}-src-{env.name}"
        source.write_text(blob)
        selected = env.context or _current_context(source)
        if selected and selected != env.name:
            subprocess.run(
                ["kubectl", "config", f"--kubeconfig={source}", "rename-context", selected, env.name],
                capture_output=True,
                text=True,
                check=True,
            )
        sources.append(str(source))

    merged = Path(workspace) / WORKSPACE_KUBECONFIG
    view = subprocess.run(
        ["kubectl", "config", "view", "--flatten"],
        env={**os.environ, "KUBECONFIG": ":".join(sources)},
        capture_output=True,
        text=True,
        check=True,
    )
    merged.write_text(view.stdout)
    subprocess.run(
        ["kubectl", "config", f"--kubeconfig={merged}", "use-context", kube_envs[0].name],
        capture_output=True,
        text=True,
        check=True,
    )
    for src in sources:
        Path(src).unlink(missing_ok=True)
    return merged


def dynamic_client_for(env: Environment, workspace: Path) -> dynamic.DynamicClient:
    """Build a dynamic client for a kubernetes environment from its workspace kubeconfig.

    The client's resource discovery is invalidated before use so a resource whose
    scope changed on the server (as the WorkloadPlan did, Namespaced to Cluster)
    is re-discovered rather than read from a stale on-disk cache. Without this a
    long-lived process keeps treating the plan as namespaced and rejects a
    cluster-scoped apply with "Namespace is required".

    Parameters
    ----------
    env
        The kubernetes environment to connect to.
    workspace
        Directory the kubeconfig is materialized into.

    Returns
    -------
    dynamic.DynamicClient
        A client scoped to the environment's kubeconfig and context.
    """
    path = materialize_kubeconfig(env, workspace)
    api = config.new_client_from_config(config_file=str(path), context=env.context)
    client = dynamic.DynamicClient(api)
    client.resources.invalidate_cache()
    return client


def apply_cr(client: dynamic.DynamicClient, cr: dict) -> dict:
    """Server-side apply a WorkloadPlan custom resource. Idempotent.

    The plan is cluster-scoped, so it is applied with no namespace; its children
    carry their own namespaces in their manifests.

    Parameters
    ----------
    client
        A dynamic client for the target environment.
    cr
        The WorkloadPlan resource body to apply.

    Returns
    -------
    dict
        The applied resource as returned by the API server.
    """
    resource = client.resources.get(api_version=API_VERSION, kind=KIND)
    applied = client.server_side_apply(
        resource,
        body=cr,
        name=cr["metadata"]["name"],
        field_manager=FIELD_MANAGER,
        force_conflicts=True,
    )
    return applied.to_dict()


def get_cr(client: dynamic.DynamicClient, name: str) -> dict | None:
    """Read a cluster-scoped WorkloadPlan as a full object dict, or None if absent.

    Parameters
    ----------
    client
        A dynamic client for the target environment.
    name
        The WorkloadPlan name.

    Returns
    -------
    dict or None
        The whole resource, or None when the plan is absent.
    """
    resource = client.resources.get(api_version=API_VERSION, kind=KIND)
    try:
        obj = resource.get(name=name)
    except ApiException as exc:
        if exc.status == 404:
            return None
        raise
    return obj.to_dict()


def list_crs(client: dynamic.DynamicClient) -> list[dict]:
    """List every WorkloadPlan in the cluster as object dicts.

    Parameters
    ----------
    client
        A dynamic client for the target environment.

    Returns
    -------
    list of dict
        Every WorkloadPlan in the cluster.
    """
    resource = client.resources.get(api_version=API_VERSION, kind=KIND)
    listing = resource.get()
    return [item.to_dict() for item in listing.items]


def delete_cr(client: dynamic.DynamicClient, name: str) -> None:
    """Delete a cluster-scoped WorkloadPlan; ownerReferences cascade-delete its children.

    Parameters
    ----------
    client
        A dynamic client for the target environment.
    name
        The WorkloadPlan name.
    """
    resource = client.resources.get(api_version=API_VERSION, kind=KIND)
    resource.delete(name=name)


def list_events(client: dynamic.DynamicClient, namespace: str, involved_name: str) -> list[dict]:
    """List the Kubernetes events for one object in a namespace, as object dicts.

    Used to dive deeper when a plan will not converge: the reason a child is stuck
    (an image that will not pull, a pod that will not schedule) and the operator's
    own reconcile failures are recorded as events on the involved object, not in
    the plan status, so this reads them back.

    Parameters
    ----------
    client
        A dynamic client for the target environment.
    namespace
        Namespace the events live in; for a cluster-scoped object the operator's
        events are posted to the default namespace.
    involved_name
        The metadata.name of the object whose events are wanted.

    Returns
    -------
    list of dict
        Every event whose involvedObject has the given name. Empty when none or
        when events cannot be read.
    """
    resource = client.resources.get(api_version="v1", kind="Event")
    listing = resource.get(namespace=namespace, field_selector=f"involvedObject.name={involved_name}")
    return [item.to_dict() for item in listing.items]


def get_cr_status(client: dynamic.DynamicClient, name: str) -> dict | None:
    """Read a cluster-scoped WorkloadPlan's status, or None if the resource is absent.

    Parameters
    ----------
    client
        A dynamic client for the target environment.
    name
        The WorkloadPlan name.

    Returns
    -------
    dict or None
        The status subresource, or None when the plan is absent.
    """
    resource = client.resources.get(api_version=API_VERSION, kind=KIND)
    try:
        obj = resource.get(name=name)
    except ApiException as exc:
        if exc.status == 404:
            return None
        raise
    return obj.to_dict().get("status", {})
