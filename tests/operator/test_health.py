"""Unit tests for the per-kind health adapters (is_ready).

Each adapter is pure: a live object dict in, a Health triple out. These pin the
ready / pending / failed outcomes that compute_phase later aggregates.
"""

from workload_operator.core import fatal_pod_reason, is_ready, pod_selector


def test_deployment_ready_when_replicas_met():
    obj = {"spec": {"replicas": 2}, "status": {"readyReplicas": 2}}
    health = is_ready("Deployment", obj)
    assert health.ready and not health.failed


def test_deployment_pending_when_replicas_short():
    obj = {"spec": {"replicas": 3}, "status": {"readyReplicas": 1}}
    health = is_ready("Deployment", obj)
    assert not health.ready and not health.failed


def test_deployment_failed_on_progress_deadline_exceeded():
    obj = {
        "spec": {"replicas": 1},
        "status": {
            "readyReplicas": 0,
            "conditions": [{"type": "Progressing", "status": "False", "reason": "ProgressDeadlineExceeded"}],
        },
    }
    health = is_ready("Deployment", obj)
    assert health.failed and not health.ready


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


def _pod(name, reason=None, restarts=0):
    waiting = {"reason": reason} if reason else {}
    return {
        "metadata": {"name": name},
        "status": {"containerStatuses": [{"name": "c", "restartCount": restarts, "state": {"waiting": waiting}}]},
    }


def test_fatal_pod_reason_flags_crashloop():
    reason = fatal_pod_reason([_pod("crasher-1", reason="CrashLoopBackOff")])
    assert reason == "crasher-1: CrashLoopBackOff"


def test_fatal_pod_reason_flags_image_pull_failure():
    reason = fatal_pod_reason([_pod("puller-1", reason="ImagePullBackOff")])
    assert reason == "puller-1: ImagePullBackOff"


def test_fatal_pod_reason_flags_excessive_restarts():
    reason = fatal_pod_reason([_pod("flapper-1", restarts=3)])
    assert reason is not None and "restarted 3 times" in reason


def test_fatal_pod_reason_none_when_pods_healthy():
    assert fatal_pod_reason([_pod("ok-1", restarts=1)]) is None
    assert fatal_pod_reason([]) is None


def test_pod_selector_extracts_match_labels():
    assert pod_selector({"spec": {"selector": {"matchLabels": {"app": "web"}}}}) == {"app": "web"}
    assert pod_selector({"spec": {}}) == {}
