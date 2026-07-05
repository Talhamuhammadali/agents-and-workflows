"""Kopf handlers for the WorkloadPlan operator (the hands).

Each handler is deliberately thin: parse the resource into typed models, call
the pure decision functions in core, and perform the resulting I/O. Any real
branching lives in core with a unit test, not here. Handlers are synchronous
because the kubernetes client is synchronous; Kopf runs them in a thread pool.
"""

import json
from typing import Any

import kopf

from workload_operator.constants import DEFAULT_NAMESPACE, GROUP, LABEL_OWNER, LABEL_SESSION, PLURAL, VERSION
from workload_operator.core import (
    Health,
    build_child,
    component_namespace,
    fatal_pod_reason,
    is_ready,
    orphaned_children,
    plan_status_digest,
    pod_selector,
)
from workload_operator.k8s import apply_manifest, delete_object, dynamic_client, get_object, list_pods
from workload_operator.models import ChildStatus, OwnerMeta, parse_spec

HEALTH_INTERVAL = 15.0
POD_OWNING_KINDS = frozenset({"Deployment"})


def _apply_error(exc: Exception) -> str:
    """Render a cluster error as a short child note, preferring the API message.

    A kubernetes API error carries the useful sentence (why an apply was refused)
    in its JSON body message; fall back to its reason or str form. Kept short so
    it reads as a status note, never a stack dump.
    """
    body = getattr(exc, "body", None)
    if body:
        try:
            message = json.loads(body).get("message")
            if message:
                return f"apply failed: {message}"[:300]
        except (ValueError, TypeError):
            pass
    return f"apply failed: {getattr(exc, 'reason', None) or exc}"[:300]


def _owner_meta(name: str, uid: str, meta: kopf.Meta) -> OwnerMeta:
    """Assemble the owning-plan identity from the resource metadata."""
    labels = meta.get("labels", {})
    return OwnerMeta(
        name=name,
        uid=uid,
        session=labels.get(LABEL_SESSION, ""),
        owner=labels.get(LABEL_OWNER, ""),
    )


def _prune_orphans(client: Any, desired_names: set[str], status: Any, logger: Any) -> None:
    """Delete children recorded in status whose component left the spec.

    Kind-agnostic and namespace-aware: it deletes whatever was recorded, in the
    namespace it was recorded in, so a removed component is pruned wherever the
    cluster-scoped plan placed it, with no fixed kind or namespace list.
    """
    recorded = (status or {}).get("children", [])
    live = [
        {
            "component": child.get("name"),
            "kind": child.get("kind"),
            "api_version": child.get("apiVersion"),
            "name": child.get("objectName"),
            "namespace": child.get("namespace") or DEFAULT_NAMESPACE,
        }
        for child in recorded
    ]
    for orphan in orphaned_children(desired_names, live):
        if orphan["api_version"] and orphan["name"]:
            delete_object(client, orphan["api_version"], orphan["kind"], orphan["name"], orphan["namespace"])
            logger.info(f"pruned orphaned child {orphan['kind']}/{orphan['name']} in {orphan['namespace']}")


@kopf.on.create(GROUP, VERSION, PLURAL)
@kopf.on.update(GROUP, VERSION, PLURAL)
@kopf.on.resume(GROUP, VERSION, PLURAL)
def reconcile(
    spec: kopf.Spec,
    meta: kopf.Meta,
    status: kopf.Status,
    name: str,
    uid: str,
    patch: kopf.Patch,
    logger: Any,
    **_: Any,
) -> None:
    """Apply every component as an owned child, prune removed ones, seed status.

    Idempotent via server-side apply, so create, update, and resume all reuse
    it. Each child is placed in the namespace its manifest declares, since the
    plan is cluster-scoped. Pruning diffs the previously recorded children
    against the current spec, so a component dropped from the plan has its child
    deleted. The health timer, not this handler, decides readiness.
    """
    plan = parse_spec(dict(spec))
    owner = _owner_meta(name, uid, meta)
    client = dynamic_client()
    children: list[ChildStatus] = []
    for component in plan.components:
        manifest = component.manifest
        namespace = component_namespace(component)
        base = {
            "name": component.name,
            "kind": manifest.kind,
            "namespace": namespace,
            "apiVersion": manifest.apiVersion,
            "objectName": manifest.metadata.name,
        }
        try:
            apply_manifest(client, build_child(component, owner))
            children.append(ChildStatus(**base))
        except Exception as exc:
            note = _apply_error(exc)
            logger.error(f"component '{component.name}': {note}")
            children.append(ChildStatus(**base, failed=True, note=note))
    _prune_orphans(client, {component.name for component in plan.components}, status, logger)
    digest = plan_status_digest(children)
    digest["observedGeneration"] = meta.get("generation")
    patch.status.update(digest)
    logger.info(f"reconciled {len(children)} component(s)")


@kopf.on.delete(GROUP, VERSION, PLURAL)
def on_delete(name: str, logger: Any, **_: Any) -> None:
    """Do nothing but log; ownerReferences cascade-delete the children."""
    logger.info(f"plan {name} deleted; children removed by cascade garbage collection")


@kopf.timer(GROUP, VERSION, PLURAL, interval=HEALTH_INTERVAL)
def health_sweep(
    spec: kopf.Spec,
    meta: kopf.Meta,
    name: str,
    uid: str,
    patch: kopf.Patch,
    logger: Any,
    **_: Any,
) -> None:
    """Reassess each child's health, self-heal missing ones, patch the digest."""
    plan = parse_spec(dict(spec))
    owner = _owner_meta(name, uid, meta)
    client = dynamic_client()
    children: list[ChildStatus] = []
    for component in plan.components:
        manifest = component.manifest
        kind = manifest.kind
        namespace = component_namespace(component)
        base = {
            "name": component.name,
            "kind": kind,
            "namespace": namespace,
            "apiVersion": manifest.apiVersion,
            "objectName": manifest.metadata.name,
        }
        try:
            live = get_object(client, manifest.apiVersion, kind, manifest.metadata.name, namespace)
            if live is None:
                apply_manifest(client, build_child(component, owner))
                children.append(ChildStatus(**base, note="recreated"))
                continue
            health = is_ready(kind, live)
            if kind in POD_OWNING_KINDS and not health.ready:
                reason = fatal_pod_reason(list_pods(client, namespace, pod_selector(live)))
                if reason:
                    health = Health(ready=False, failed=True, note=reason)
            children.append(ChildStatus(**base, ready=health.ready, failed=health.failed, note=health.note))
        except Exception as exc:
            note = _apply_error(exc)
            logger.error(f"component '{component.name}': {note}")
            children.append(ChildStatus(**base, failed=True, note=note))
    digest = plan_status_digest(children)
    digest["observedGeneration"] = meta.get("generation")
    patch.status.update(digest)
