"""Pydantic models mirroring the WorkloadPlan CRD.

Single source of truth on the operator side. The Kopf handlers parse the raw
resource body into these models, so the reconciliation logic works with typed
objects that stay aligned with crd.yaml instead of loose dict access. Field
names deliberately match the CRD (camelCase where Kubernetes uses it) so a
model round-trips to the resource body without translation, and every field
carries a description so the model doubles as living documentation of the
contract.

The split mirrors the seam in the design: the agent authors the spec models,
the operator owns the status models. Neither side writes the other's fields.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Phase = Literal["Pending", "Ready", "Failed"]
Intent = Literal["migrate", "provision"]


class ObjectMeta(BaseModel):
    """The metadata of an embedded object; name is required so it can be applied.

    Only name is pinned; labels, annotations, and the rest are preserved
    verbatim, mirroring the CRD.
    """

    model_config = ConfigDict(extra="allow")

    name: str = Field(description="Name of the object, required to apply and health-check it.")


class Manifest(BaseModel):
    """A raw Kubernetes object embedded in a component.

    Only apiVersion, kind, and metadata.name are pinned; every other field is
    preserved verbatim, which is the model-side mirror of the CRD
    preserve-unknown behaviour that lets the operator adopt an arbitrary
    manifest without the schema knowing its shape.
    """

    model_config = ConfigDict(extra="allow")

    apiVersion: str = Field(description="API group and version of the embedded object, for example apps/v1.")
    kind: str = Field(description="Kind of the embedded object, for example Deployment or Job.")
    metadata: ObjectMeta = Field(description="Object metadata; must carry a name.")


class Component(BaseModel):
    """One named workload piece the operator adopts, owns, and watches."""

    name: str = Field(description="Unique name of the component within the plan; the CRD list merge key.")
    manifest: Manifest = Field(description="The raw Kubernetes object this component materializes.")


class WorkloadPlanSpec(BaseModel):
    """Desired state authored by the agent; the operator never writes it."""

    intent: Intent | None = Field(
        default=None,
        description="Attribution label only, never a control-flow branch. Either migrate or provision.",
    )
    components: list[Component] = Field(
        min_length=1,
        description="The workloads the operator materializes and owns. At least one is required.",
    )


class ChildStatus(BaseModel):
    """Last-known health digest for one adopted child.

    This is what the polling agent reads per child: whether it is ready,
    whether it terminally failed, and a short note carrying the reason, so the
    agent can explain a failure without a separate channel.
    """

    name: str = Field(description="Name of the child, matching its source component.")
    kind: str = Field(description="Kubernetes kind of the child, used to pick its health adapter.")
    apiVersion: str = Field(
        default="", description="API version of the applied object, recorded so any kind can be pruned."
    )
    objectName: str = Field(
        default="", description="Name of the applied object, recorded for pruning and health lookups."
    )
    ready: bool = Field(default=False, description="True once the child's health adapter reports it healthy.")
    failed: bool = Field(
        default=False, description="True when the child terminally failed, for example a Job past its backoff limit."
    )
    note: str = Field(default="", description="Short human-readable reason for the current state, never a log dump.")


class Condition(BaseModel):
    """A Kubernetes-style status condition, including NeedsAttention on failure."""

    type: str = Field(description="Condition type, for example NeedsAttention.")
    status: str = Field(description="Condition status, one of True, False, or Unknown.")
    reason: str = Field(default="", description="Short machine-readable reason code.")
    message: str = Field(default="", description="Human-readable detail naming the offending child.")


class WorkloadPlanStatus(BaseModel):
    """Status owned and written by the operator; never written by the agent."""

    phase: Phase = Field(default="Pending", description="Aggregate lifecycle phase computed from the children.")
    observedGeneration: int = Field(
        default=0, description="The spec generation this status reflects, to detect stale status."
    )
    readyCount: int = Field(default=0, description="Number of children currently reporting ready.")
    children: list[ChildStatus] = Field(
        default_factory=list, description="Per-child health digest the agent polls for a breakdown."
    )
    conditions: list[Condition] = Field(
        default_factory=list, description="Standard conditions, carrying the escalation signal on failure."
    )


class OwnerMeta(BaseModel):
    """Identity of the owning WorkloadPlan, derived from its metadata.

    Not a CRD section: the operator assembles this from the plan being
    reconciled and hands it to build_child, which stamps it onto every child as
    an ownerReference plus attribution labels. This is what makes the plan the
    root of an ownership tree the whole session can be queried and cascade
    deleted by.
    """

    name: str = Field(description="Name of the owning plan.")
    uid: str = Field(description="UID of the owning plan, required for a valid ownerReference.")
    namespace: str = Field(description="Namespace the plan and its children live in.")
    session: str = Field(default="", description="Agent session id propagated to children for attribution.")
    owner: str = Field(default="", description="Requesting user propagated to children for attribution.")


def parse_spec(spec: dict[str, Any]) -> WorkloadPlanSpec:
    """Parse a raw resource spec body into the typed spec model.

    Parameters
    ----------
    spec : dict
        The spec section of a WorkloadPlan as handed to a Kopf handler.

    Returns
    -------
    WorkloadPlanSpec
        The validated, typed spec.
    """
    return WorkloadPlanSpec.model_validate(spec)
