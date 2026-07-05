"""Gate 1 model and CR translation for the WorkloadPlan provisioning capability."""

from copy import deepcopy
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from workload_operator.constants import API_VERSION, KIND

ANN_SOURCE_REF = "poc.local/source-ref"
ANN_ACCEPTED_LOSSES = "poc.local/accepted-losses"

Intent = Literal["migrate", "provision"]


class Component(BaseModel):
    """One named component of a plan, wrapping a raw Kubernetes manifest.

    Parameters
    ----------
    name
        Unique name for the component within the plan.
    manifest
        A complete Kubernetes object, requiring apiVersion, kind and
        metadata.name.
    source_ref
        For a migration, where the manifest came from in the source.
    accepted_losses
        For a migration, declared lossy mappings the user has accepted.
    """

    name: str = Field(description="Unique name for the component within the plan.")
    manifest: dict = Field(description="A complete Kubernetes object with apiVersion, kind and metadata.name.")
    source_ref: str | None = Field(default=None, description="For a migration, the source the manifest came from.")
    accepted_losses: list[str] = Field(default_factory=list, description="Declared lossy mappings the user accepted.")

    @field_validator("manifest")
    @classmethod
    def _manifest_is_well_formed(cls, manifest: dict) -> dict:
        """Reject a manifest missing apiVersion, kind or metadata.name."""
        if not manifest.get("apiVersion"):
            raise ValueError("manifest requires apiVersion")
        if not manifest.get("kind"):
            raise ValueError("manifest requires kind")
        if not (manifest.get("metadata") or {}).get("name"):
            raise ValueError("manifest requires metadata.name")
        return manifest


class PlanModel(BaseModel):
    """The agent's Gate 1 decision vocabulary, validated before a CR is submitted.

    Parameters
    ----------
    intent
        Whether the plan migrates existing infrastructure or provisions new.
    components
        The components to declare, at least one, with unique names.
    """

    intent: Intent = Field(description="Whether the plan migrates existing infrastructure or provisions new.")
    components: list[Component] = Field(min_length=1, description="The components to declare, with unique names.")

    @model_validator(mode="after")
    def _names_are_unique(self) -> "PlanModel":
        """Reject duplicate component names."""
        names = [c.name for c in self.components]
        if len(names) != len(set(names)):
            raise ValueError("component names must be unique")
        return self


def build_workload_plan(plan: PlanModel, name: str, namespace: str | None = None) -> dict:
    """Translate a validated PlanModel into a WorkloadPlan custom resource.

    The plan is cluster-scoped, so each component is placed by its manifest's own
    namespace; when a manifest omits one and a target namespace is given, that
    target is stamped on so the component lands where the run is aimed rather
    than in the operator's default. Each component's migration metadata is folded
    into its manifest annotations so the declared losses live in the CR, not only
    in chat. Pre-existing metadata is preserved and the caller's manifests are
    never mutated.

    Parameters
    ----------
    plan
        The validated plan to translate.
    name
        The metadata.name for the WorkloadPlan resource.
    namespace
        Target namespace stamped onto any component manifest that omits one.

    Returns
    -------
    dict
        A WorkloadPlan custom resource ready to apply.
    """
    components = []
    for component in plan.components:
        manifest = deepcopy(component.manifest)
        metadata = manifest.setdefault("metadata", {})
        if namespace and not metadata.get("namespace"):
            metadata["namespace"] = namespace
        annotations = {**metadata.get("annotations", {})}
        if component.source_ref:
            annotations[ANN_SOURCE_REF] = component.source_ref
        if component.accepted_losses:
            annotations[ANN_ACCEPTED_LOSSES] = "; ".join(component.accepted_losses)
        if annotations:
            metadata["annotations"] = annotations
        components.append({"name": component.name, "manifest": manifest})

    return {
        "apiVersion": API_VERSION,
        "kind": KIND,
        "metadata": {"name": name},
        "spec": {"intent": plan.intent, "components": components},
    }
