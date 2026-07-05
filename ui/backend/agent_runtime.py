"""Which agent the UI serves, and how its per-run context is built from thread config.

The UI serves the infrastructure agent. Its environments come from the thread's
connection config (entered once per thread): AWS credentials for the source, and
a target that is either the local minikube (read from the mounted kubeconfig) or
a pasted flattened kubeconfig for a remote cluster. allow_bash unlocks the
fileops skill so the agent can validate the CRD with kubectl.
"""

import subprocess
from pathlib import Path

from agentic_patterns.infra_agent.agent import INFRA_AGENT_BUILDER
from agentic_patterns.infra_agent.prompts import INFRA_AGENT_SYSTEM_PROMPT, render_environments
from agentic_patterns.infra_agent.state import Credentials, Environment, InfraAgentContext
from agentic_patterns.infra_agent.tools.clients import materialize_workspace_kubeconfig
from ui.backend.models import ThreadConfig
from utils.llms import Model

BUILDER = INFRA_AGENT_BUILDER
AGENT_NAME = "Infra Agent"
LOCAL_KUBECONFIG = "/host/.kube/config"


def _local_minikube_blob(context: str = "minikube") -> str | None:
    """Snapshot the mounted local kubeconfig as a self-contained blob for one context."""
    try:
        result = subprocess.run(
            [
                "kubectl",
                "config",
                "view",
                "--minify",
                "--flatten",
                f"--context={context}",
                f"--kubeconfig={LOCAL_KUBECONFIG}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout or None


def _environments(config: ThreadConfig) -> list[Environment]:
    """Translate a thread's connection config into the agent's reachable environments."""
    environments: list[Environment] = []
    if config.aws is not None:
        environments.append(
            Environment(
                name="aws",
                kind="aws",
                credentials=Credentials(
                    access_key_id=config.aws.access_key_id,
                    secret_access_key=config.aws.secret_access_key,
                    region=config.aws.region,
                    session_token=config.aws.session_token,
                ),
            )
        )
    if config.use_local_minikube:
        blob = _local_minikube_blob()
        if blob is not None:
            environments.append(
                Environment(
                    name="minikube",
                    kind="kubernetes",
                    kubeconfig=blob,
                    context="minikube",
                    namespace=config.target_namespace,
                )
            )
    elif config.target_kubeconfig:
        environments.append(
            Environment(
                name="target",
                kind="kubernetes",
                kubeconfig=config.target_kubeconfig,
                context=None,
                namespace=config.target_namespace,
            )
        )
    return environments


def build_context(model: Model, workspace: Path, config: ThreadConfig) -> InfraAgentContext:
    """Assemble the per-run infrastructure agent context from a thread's config."""
    skills = ["k8s", "fileops"] if config.allow_bash else ["k8s"]
    environments = _environments(config)
    kubeconfig = materialize_workspace_kubeconfig(environments, workspace)
    bash_env = {"KUBECONFIG": str(kubeconfig)} if kubeconfig else None
    return InfraAgentContext(
        workspace=workspace,
        system_prompt=INFRA_AGENT_SYSTEM_PROMPT + render_environments(environments),
        agent_name=AGENT_NAME,
        available_skills=skills,
        model=model.value,
        environments=environments,
        bash_env=bash_env,
    )
