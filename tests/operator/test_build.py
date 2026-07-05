"""Unit tests for build_child and plan_status_digest.

build_child is the ownership-ledger mechanism: ownerReference plus attribution
labels. plan_status_digest is the status patch the operator writes back.
"""

from workload_operator.constants import (
    API_VERSION,
    KIND,
    LABEL_COMPONENT,
    LABEL_OWNER,
    LABEL_PLAN,
    LABEL_SESSION,
)
from workload_operator.core import build_child, component_namespace, plan_status_digest
from workload_operator.models import ChildStatus, Component, OwnerMeta


def _component(namespace: str | None = None):
    metadata: dict = {"name": "web", "labels": {"team": "platform"}}
    if namespace is not None:
        metadata["namespace"] = namespace
    return Component(
        name="web",
        manifest={
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": metadata,
            "spec": {"replicas": 2},
        },
    )


def _owner():
    return OwnerMeta(name="migrate-web", uid="uid-123", session="sess-9", owner="talha")


def test_build_child_stamps_owner_reference():
    child = build_child(_component(), _owner())
    ref = child["metadata"]["ownerReferences"][0]
    assert ref["apiVersion"] == API_VERSION
    assert ref["kind"] == KIND
    assert ref["name"] == "migrate-web"
    assert ref["uid"] == "uid-123"
    assert ref["controller"] is True


def test_build_child_stamps_attribution_labels():
    child = build_child(_component(), _owner())
    labels = child["metadata"]["labels"]
    assert labels[LABEL_PLAN] == "migrate-web"
    assert labels[LABEL_COMPONENT] == "web"
    assert labels[LABEL_SESSION] == "sess-9"
    assert labels[LABEL_OWNER] == "talha"


def test_build_child_preserves_existing_labels_and_spec():
    child = build_child(_component(), _owner())
    assert child["metadata"]["labels"]["team"] == "platform"
    assert child["spec"]["replicas"] == 2


def test_build_child_defaults_namespace_when_manifest_omits_it():
    child = build_child(_component(), _owner())
    assert child["metadata"]["namespace"] == "default"


def test_build_child_keeps_manifest_namespace():
    child = build_child(_component(namespace="team-a"), _owner())
    assert child["metadata"]["namespace"] == "team-a"


def test_component_namespace_reads_manifest_then_defaults():
    assert component_namespace(_component(namespace="team-a")) == "team-a"
    assert component_namespace(_component()) == "default"


def test_build_child_does_not_mutate_input_component():
    component = _component()
    build_child(component, _owner())
    assert "ownerReferences" not in component.manifest.model_dump().get("metadata", {})


def _child(name, ready=False, failed=False):
    return ChildStatus(name=name, kind="Deployment", ready=ready, failed=failed)


def test_digest_reports_phase_and_ready_count():
    digest = plan_status_digest([_child("a", ready=True), _child("b")])
    assert digest["phase"] == "Pending"
    assert digest["readyCount"] == 1


def test_digest_emits_needs_attention_condition_on_failure():
    digest = plan_status_digest([_child("a", ready=True), _child("b", failed=True)])
    assert digest["phase"] == "Failed"
    condition = digest["conditions"][0]
    assert condition["type"] == "NeedsAttention"
    assert "b" in condition["message"]


def test_digest_has_no_conditions_when_healthy():
    digest = plan_status_digest([_child("a", ready=True)])
    assert digest["phase"] == "Ready"
    assert digest["conditions"] == []
