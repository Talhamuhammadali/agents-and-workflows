"""Fixtures for the infrastructure agent integration tests.

Reuses the operator's minikube-guarded, per-test-namespace fixtures so the agent
tests run in the same isolated namespaces, and adds a helper that snapshots the
local minikube kubeconfig as a self-contained blob the agent can be handed.
"""

import subprocess

from tests.operator.conftest import cluster, crd_applied, namespace

__all__ = ["cluster", "crd_applied", "namespace", "minikube_kubeconfig"]


def minikube_kubeconfig() -> str:
    """Return a self-contained kubeconfig for the local minikube context.

    The flatten flag inlines the certificate data so the blob carries no
    file-path references and can be written into a workspace and loaded alone.
    """
    result = subprocess.run(
        ["kubectl", "config", "view", "--minify", "--flatten", "--context=minikube"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout
