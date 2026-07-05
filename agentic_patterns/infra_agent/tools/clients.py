"""Cluster client seam for the infrastructure agent.

The target client is always built from a kubeconfig written into the workspace
and loaded explicitly, so the agent can only ever reach the environment it was
handed and never the ambient default context.
"""

from pathlib import Path

from kubernetes import config, dynamic
from kubernetes.client.exceptions import ApiException

from agentic_patterns.infra_agent.state import Environment
from workload_operator.constants import API_VERSION, KIND

FIELD_MANAGER = "infra-agent"


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


def dynamic_client_for(env: Environment, workspace: Path) -> dynamic.DynamicClient:
    """Build a dynamic client for a kubernetes environment from its workspace kubeconfig.

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
    return dynamic.DynamicClient(api)


def apply_cr(client: dynamic.DynamicClient, cr: dict, namespace: str) -> dict:
    """Server-side apply a WorkloadPlan custom resource. Idempotent.

    Parameters
    ----------
    client
        A dynamic client for the target environment.
    cr
        The WorkloadPlan resource body to apply.
    namespace
        Namespace to apply the resource in.

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
        namespace=namespace,
        field_manager=FIELD_MANAGER,
        force_conflicts=True,
    )
    return applied.to_dict()


def get_cr_status(client: dynamic.DynamicClient, name: str, namespace: str) -> dict | None:
    """Read a WorkloadPlan's status, or None if the resource does not exist.

    Parameters
    ----------
    client
        A dynamic client for the target environment.
    name
        The WorkloadPlan name.
    namespace
        Namespace the resource lives in.

    Returns
    -------
    dict or None
        The status subresource, or None when the plan is absent.
    """
    resource = client.resources.get(api_version=API_VERSION, kind=KIND)
    try:
        obj = resource.get(name=name, namespace=namespace)
    except ApiException as exc:
        if exc.status == 404:
            return None
        raise
    return obj.to_dict().get("status", {})
