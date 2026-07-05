"""Pure decision functions for the WorkloadPlan operator.

These hold the operator's reconciliation logic with no Kubernetes I/O: typed
models and plain dicts in, plain values out. That is what lets them be
unit-tested at millisecond speed with no cluster, per the spec-01 TDD strategy
(the brain; the Kopf handlers are the hands).
"""

from collections.abc import Callable
from typing import Any, NamedTuple

from workload_operator.constants import (
    API_VERSION,
    DEFAULT_NAMESPACE,
    KIND,
    LABEL_COMPONENT,
    LABEL_OWNER,
    LABEL_PLAN,
    LABEL_SESSION,
)
from workload_operator.models import ChildStatus, Component, OwnerMeta, Phase

FATAL_WAITING_REASONS = frozenset(
    {"CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull", "CreateContainerConfigError", "InvalidImageName"}
)
RESTART_THRESHOLD = 3


class Health(NamedTuple):
    """The outcome of assessing one live child object.

    Three-valued on purpose: a workload can be healthy, still converging, or
    terminally failed, and the plan phase needs to tell converging apart from
    failed. The note is a short reason, never a log dump.
    """

    ready: bool
    failed: bool
    note: str


def compute_phase(children: list[ChildStatus]) -> Phase:
    """Aggregate per-child health into a single plan phase.

    Parameters
    ----------
    children : list of ChildStatus
        One entry per reconciled child, carrying its ready and failed state.

    Returns
    -------
    {"Pending", "Ready", "Failed"}
        Failed if any child has failed; Ready only if there is at least one
        child and every child is ready; Pending otherwise (including the empty
        list, before reconciliation has populated it).
    """
    if any(child.failed for child in children):
        return "Failed"
    if children and all(child.ready for child in children):
        return "Ready"
    return "Pending"


def _progress_deadline_exceeded(status: dict[str, Any]) -> bool:
    """True when the Deployment's own conditions report the rollout has given up.

    ProgressDeadlineExceeded is the single terminal signal a Deployment writes
    onto its own object: unlike a Job it never counts failures, so this is how a
    stalled rollout (an image that will not pull, pods that never schedule)
    becomes failed rather than pending forever.
    """
    for condition in status.get("conditions", []):
        if (
            condition.get("type") == "Progressing"
            and condition.get("status") == "False"
            and condition.get("reason") == "ProgressDeadlineExceeded"
        ):
            return True
    return False


def _deployment_health(obj: dict[str, Any]) -> Health:
    """Ready once ready replicas meet the desired count; failed once the rollout deadline is exceeded."""
    spec = obj.get("spec", {})
    status = obj.get("status", {})
    desired = spec.get("replicas", 1)
    ready_replicas = status.get("readyReplicas", 0)
    if _progress_deadline_exceeded(status):
        return Health(ready=False, failed=True, note="rollout stalled: progress deadline exceeded")
    note = f"{ready_replicas}/{desired} replicas ready"
    return Health(ready=ready_replicas >= desired, failed=False, note=note)


def pod_selector(obj: dict[str, Any]) -> dict[str, str]:
    """Return the matchLabels a workload controller uses to own its pods, or an empty dict."""
    selector = (obj.get("spec", {}) or {}).get("selector", {}) or {}
    return selector.get("matchLabels", {}) or {}


def fatal_pod_reason(pods: list[dict[str, Any]], restart_threshold: int = RESTART_THRESHOLD) -> str | None:
    """Return a short reason if any pod is terminally stuck, else None.

    Terminal means a container is in a fatal waiting state (a crash loop, or an
    image it cannot pull or configure) or has restarted past the threshold. A
    Deployment never surfaces this on its own object, so the operator reads it
    from the pods to escalate a crash loop instead of reporting pending forever.

    Parameters
    ----------
    pods : list of dict
        The live pods owned by the workload, each carrying status.containerStatuses.
    restart_threshold : int
        Restart count at or above which a container is treated as terminally failed.

    Returns
    -------
    str or None
        A short reason naming the offending pod and cause, or None when no pod
        is terminally stuck.
    """
    for pod in pods:
        pod_name = (pod.get("metadata", {}) or {}).get("name", "pod")
        for container in (pod.get("status", {}) or {}).get("containerStatuses", []) or []:
            reason = ((container.get("state", {}) or {}).get("waiting") or {}).get("reason")
            if reason in FATAL_WAITING_REASONS:
                return f"{pod_name}: {reason}"
            restarts = container.get("restartCount", 0)
            if restarts >= restart_threshold:
                return f"{pod_name}: container {container.get('name', '?')} restarted {restarts} times"
    return None


def _job_health(obj: dict[str, Any]) -> Health:
    """Ready when the job has succeeded; failed once failures exceed the backoff limit."""
    spec = obj.get("spec", {})
    status = obj.get("status", {})
    backoff_limit = spec.get("backoffLimit", 6)
    succeeded = status.get("succeeded", 0)
    failed = status.get("failed", 0)
    if succeeded >= 1:
        return Health(ready=True, failed=False, note="job complete")
    if failed > backoff_limit:
        return Health(ready=False, failed=True, note=f"job failed: {failed} attempts past backoffLimit {backoff_limit}")
    return Health(ready=False, failed=False, note="job running")


def _pod_health(obj: dict[str, Any]) -> Health:
    """Ready when the pod is Running with every container ready; failed when the pod phase is Failed."""
    status = obj.get("status", {})
    phase = status.get("phase")
    container_statuses = status.get("containerStatuses", [])
    all_containers_ready = bool(container_statuses) and all(c.get("ready") for c in container_statuses)
    if phase == "Running" and all_containers_ready:
        return Health(ready=True, failed=False, note="running")
    if phase == "Failed":
        return Health(ready=False, failed=True, note="pod failed")
    return Health(ready=False, failed=False, note=phase or "pending")


def _exists_health(obj: dict[str, Any]) -> Health:
    """Ready as soon as the object exists, for kinds with no runtime health of their own."""
    return Health(ready=True, failed=False, note="exists")


def _unknown_health(obj: dict[str, Any]) -> Health:
    """Fallback for kinds with no registered adapter: count as ready with a note."""
    return Health(ready=True, failed=False, note="no health adapter")


HEALTH_ADAPTERS: dict[str, Callable[[dict[str, Any]], Health]] = {
    "Deployment": _deployment_health,
    "Job": _job_health,
    "Pod": _pod_health,
    "Service": _exists_health,
    "ConfigMap": _exists_health,
    "Secret": _exists_health,
}


def is_ready(kind: str, obj: dict[str, Any]) -> Health:
    """Assess one live child object's health via its per-kind adapter.

    This is the evolution seam: supporting a new kind, including a third-party
    custom resource, means adding one entry to HEALTH_ADAPTERS, never changing
    the CRD schema.

    Parameters
    ----------
    kind : str
        The Kubernetes kind of the object, used to select the adapter.
    obj : dict
        The live object as returned by the API server, carrying spec and status.

    Returns
    -------
    Health
        The ready, failed, and note assessment. Unknown kinds are treated as
        ready with an explanatory note.
    """
    adapter = HEALTH_ADAPTERS.get(kind, _unknown_health)
    return adapter(obj)


def component_namespace(component: Component) -> str:
    """Return the namespace a component targets, from its manifest, defaulting when omitted.

    The plan is cluster-scoped and has no namespace of its own, so each child is
    placed by the namespace its own manifest declares. A plan may therefore span
    namespaces. A manifest that omits the namespace lands in the default one.

    Parameters
    ----------
    component : Component
        The named component whose target namespace is being resolved.

    Returns
    -------
    str
        The manifest's metadata.namespace, or the default namespace when absent.
    """
    metadata = component.manifest.metadata.model_dump()
    return metadata.get("namespace") or DEFAULT_NAMESPACE


def build_child(component: Component, owner: OwnerMeta) -> dict[str, Any]:
    """Turn a component into the child object to apply, owned by the plan.

    Stamps an ownerReference back to the plan so cascade garbage collection
    deletes the child when the plan is deleted, and copies the attribution
    labels so the whole session is queryable by who or what created it. The
    child is placed in the namespace its own manifest declares, defaulting to
    the default namespace, since the cluster-scoped plan has none to impose.
    Existing labels on the manifest are preserved. The input is not mutated.

    Parameters
    ----------
    component : Component
        The named raw manifest authored by the agent.
    owner : OwnerMeta
        Identity of the owning plan, stamped onto the child.

    Returns
    -------
    dict
        The manifest ready for server-side apply, with namespace, labels, and
        ownerReferences set.
    """
    child = component.manifest.model_dump()
    metadata = child.setdefault("metadata", {})
    metadata.setdefault("namespace", DEFAULT_NAMESPACE)
    labels = metadata.setdefault("labels", {})
    labels[LABEL_PLAN] = owner.name
    labels[LABEL_COMPONENT] = component.name
    if owner.session:
        labels[LABEL_SESSION] = owner.session
    if owner.owner:
        labels[LABEL_OWNER] = owner.owner
    metadata["ownerReferences"] = [
        {
            "apiVersion": API_VERSION,
            "kind": KIND,
            "name": owner.name,
            "uid": owner.uid,
            "controller": True,
            "blockOwnerDeletion": True,
        }
    ]
    return child


def plan_status_digest(children: list[ChildStatus]) -> dict[str, Any]:
    """Build the status patch the operator writes back for a plan.

    A digest, never a log dump: the aggregate phase, the ready count, and the
    per-child breakdown the agent polls. On failure it also emits a
    NeedsAttention condition naming the offending children, which is the
    status-as-queue escalation channel the agent reads.

    Parameters
    ----------
    children : list of ChildStatus
        The current per-child health digests.

    Returns
    -------
    dict
        The status fields to patch: phase, readyCount, children, and conditions.
    """
    phase = compute_phase(children)
    ready_count = sum(1 for child in children if child.ready)
    conditions: list[dict[str, Any]] = []
    if phase == "Failed":
        failed_names = [child.name for child in children if child.failed]
        conditions.append(
            {
                "type": "NeedsAttention",
                "status": "True",
                "reason": "ChildFailed",
                "message": f"failed children: {', '.join(failed_names)}",
            }
        )
    return {
        "phase": phase,
        "readyCount": ready_count,
        "children": [child.model_dump() for child in children],
        "conditions": conditions,
    }


def orphaned_children(desired_names: set[str], live_children: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select live children that no longer correspond to a desired component.

    Desired-state reconcile means a component dropped from the spec should have
    its child deleted. A child is an orphan when it carries a component label
    that is not in the desired set. Children with no component label are left
    alone, since they cannot be safely attributed to a removed component.

    Parameters
    ----------
    desired_names : set of str
        The component names currently in the plan spec.
    live_children : list of dict
        Descriptors of children owned by the plan, each carrying at least a
        component key naming its source component.

    Returns
    -------
    list of dict
        The descriptors of children to delete.
    """
    orphans = []
    for child in live_children:
        component = child.get("component")
        if component and component not in desired_names:
            orphans.append(child)
    return orphans
