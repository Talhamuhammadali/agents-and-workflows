"""State and context for the infrastructure agent."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, NotRequired

from agentic_patterns.base.schemas import BaseAgentContext, BaseAgentState

EnvKind = Literal["kubernetes", "aws"]


@dataclass
class Credentials:
    """Cloud credentials fed into a boto3 session.

    Read-only is enforced by the IAM policy on these keys, not by this code.

    Parameters
    ----------
    access_key_id
        Access key id.
    secret_access_key
        Secret access key.
    region
        Default region for clients opened from the session.
    session_token
        Set only for temporary STS credentials.
    """

    access_key_id: str
    secret_access_key: str
    region: str
    session_token: str | None = None


@dataclass
class Environment:
    """One infrastructure environment the agent can reach.

    The caller supplies what exists and how to reach it; the agent decides each
    environment's role and the task topology from the user request. Which fields
    apply is determined by kind: kubernetes uses the kubeconfig fields, aws uses
    credentials.

    Parameters
    ----------
    name
        Identifier the user may refer to, such as prod-eks or local-minikube.
    kind
        Environment type, selecting which client and fields apply.
    kubeconfig
        Self-contained kubeconfig blob for a kubernetes environment, cert data
        inlined. Written to the workspace and loaded explicitly.
    context
        Context name to select inside kubeconfig.
    namespace
        Default namespace for a kubernetes environment.
    credentials
        Credentials for a cloud environment.
    """

    name: str
    kind: EnvKind
    kubeconfig: str | None = None
    context: str | None = None
    namespace: str = "default"
    credentials: Credentials | None = None


class InfraAgentState(BaseAgentState):
    """Adds todos and plan_name, the resource under management this run."""

    todos: NotRequired[list[dict]]
    plan_name: NotRequired[str]


@dataclass
class InfraAgentContext(BaseAgentContext):
    """The agent's capability boundary: what it can reach, not what to do.

    Parameters
    ----------
    workspace
        Filesystem root for the workspace tools, materialized kubeconfigs, and
        any inventory the agent writes.
    environments
        Environments the agent has credentials for. May be empty. The agent
        decides roles and task topology from the user request.
    bash_env
        Extra environment layered over shell commands, used to point dev-mode
        kubectl at the workspace kubeconfig for the given environments.
    """

    workspace: Path | None = None
    environments: list[Environment] = field(default_factory=list)
    bash_env: dict[str, str] | None = None
