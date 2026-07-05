"""Unit tests for the per-kind health adapters (is_ready).

Each adapter is pure: a live object dict in, a Health triple out. These pin the
ready / pending / failed outcomes that compute_phase later aggregates.
"""

from workload_operator.core import is_ready


def test_deployment_ready_when_replicas_met():
    obj = {"spec": {"replicas": 2}, "status": {"readyReplicas": 2}}
    health = is_ready("Deployment", obj)
    assert health.ready and not health.failed


def test_deployment_pending_when_replicas_short():
    obj = {"spec": {"replicas": 3}, "status": {"readyReplicas": 1}}
    health = is_ready("Deployment", obj)
    assert not health.ready and not health.failed


def test_job_ready_when_succeeded():
    obj = {"spec": {"backoffLimit": 4}, "status": {"succeeded": 1}}
    health = is_ready("Job", obj)
    assert health.ready and not health.failed


def test_job_running_before_completion():
    obj = {"spec": {"backoffLimit": 4}, "status": {}}
    health = is_ready("Job", obj)
    assert not health.ready and not health.failed


def test_job_failed_past_backoff_limit():
    obj = {"spec": {"backoffLimit": 2}, "status": {"failed": 3}}
    health = is_ready("Job", obj)
    assert health.failed and not health.ready


def test_pod_ready_when_running_and_containers_ready():
    obj = {"status": {"phase": "Running", "containerStatuses": [{"ready": True}]}}
    health = is_ready("Pod", obj)
    assert health.ready and not health.failed


def test_pod_failed_phase():
    obj = {"status": {"phase": "Failed"}}
    health = is_ready("Pod", obj)
    assert health.failed and not health.ready


def test_exists_kinds_are_ready_immediately():
    for kind in ("Service", "ConfigMap", "Secret"):
        health = is_ready(kind, {})
        assert health.ready and not health.failed


def test_unknown_kind_counts_as_ready_with_note():
    health = is_ready("Ingress", {})
    assert health.ready and not health.failed
    assert health.note == "no health adapter"
