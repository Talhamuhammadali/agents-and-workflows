"""Regression net for build_workload_plan (the agent's analog of build_child).

This is logic the agent OWNS, not schema declaration: it assembles the CR
envelope from a validated PlanModel and folds each component's migration
metadata (source_ref, accepted_losses) into annotations so the loss is declared
in the CR itself, not just in chat. Pydantic's own validation is not retested
here on purpose. Kept deliberately small: enough to catch a regression, no more.
"""

from agentic_patterns.infra_agent.tools.models import (
    ANN_ACCEPTED_LOSSES,
    ANN_SOURCE_REF,
    Component,
    PlanModel,
    build_workload_plan,
)
from workload_operator.constants import API_VERSION, KIND


def _manifest(name: str = "web", kind: str = "Deployment") -> dict:
    return {"apiVersion": "apps/v1", "kind": kind, "metadata": {"name": name}}


def test_build_assembles_the_cr_and_folds_migration_metadata() -> None:
    plan = PlanModel(
        intent="migrate",
        components=[
            Component(
                name="ingress",
                manifest=_manifest("web", kind="Ingress"),
                source_ref="web/Ingress/web-api",
                accepted_losses=["ALB to nginx: no WAF", "no ACM cert"],
            )
        ],
    )
    cr = build_workload_plan(plan, name="migrate-web")
    assert cr["apiVersion"] == API_VERSION
    assert cr["kind"] == KIND
    assert cr["metadata"]["name"] == "migrate-web"
    assert cr["spec"]["intent"] == "migrate"
    annotations = cr["spec"]["components"][0]["manifest"]["metadata"]["annotations"]
    assert annotations[ANN_SOURCE_REF] == "web/Ingress/web-api"
    assert "no WAF" in annotations[ANN_ACCEPTED_LOSSES]
    assert "no ACM cert" in annotations[ANN_ACCEPTED_LOSSES]


def test_build_merges_with_preexisting_manifest_annotations() -> None:
    manifest = _manifest("web", kind="Ingress")
    manifest["metadata"]["annotations"] = {"team.local/owner": "platform"}
    plan = PlanModel(
        intent="migrate",
        components=[Component(name="ingress", manifest=manifest, source_ref="web/Ingress/web-api")],
    )
    cr = build_workload_plan(plan, name="migrate-web")
    annotations = cr["spec"]["components"][0]["manifest"]["metadata"]["annotations"]
    assert annotations["team.local/owner"] == "platform"
    assert annotations[ANN_SOURCE_REF] == "web/Ingress/web-api"
